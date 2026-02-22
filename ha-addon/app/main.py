"""
FastAPI server for the AI Automation Assistant.

Handles WebSocket chat, tool execution loop, and static file serving.
Designed to run inside a Home Assistant Supervisor add-on with ingress.
"""

from __future__ import annotations

import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .ha_client import HomeAssistantClient
from .llm_backends import LLMBackend, LLMResponse, create_llm_backend
from .tools import SYSTEM_PROMPT, tools_for_openai, tools_for_claude, tools_for_ollama

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("ai_automation")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OPTIONS_FILE = Path("/data/options.json")
MAX_HISTORY = 50          # messages per conversation before pruning
MAX_TOOL_ROUNDS = 8       # safety limit on tool-call loops


def load_config() -> dict[str, Any]:
    """Load config from HA Supervisor options or environment (dev fallback)."""
    if OPTIONS_FILE.exists():
        with open(OPTIONS_FILE) as f:
            return json.load(f)
    return {
        "llm_provider": os.getenv("LLM_PROVIDER", "openai"),
        "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
        "openai_model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "claude_api_key": os.getenv("CLAUDE_API_KEY", ""),
        "claude_model": os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514"),
        "ollama_url": os.getenv("OLLAMA_URL", "http://localhost:11434"),
        "ollama_model": os.getenv("OLLAMA_MODEL", "llama3"),
    }


# ---------------------------------------------------------------------------
# Globals (initialised in lifespan)
# ---------------------------------------------------------------------------

ha_client: HomeAssistantClient
llm_backend: LLMBackend
provider_name: str = ""


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    global ha_client, llm_backend, provider_name

    config = load_config()
    provider_name = config.get("llm_provider", "openai")

    # Home Assistant client — uses Supervisor API when available
    supervisor_token = os.getenv("SUPERVISOR_TOKEN", "")
    if supervisor_token:
        ha_url = "http://supervisor/core"
        ha_token = supervisor_token
    else:
        # Local development fallback
        ha_url = os.getenv("HA_URL", "http://localhost:8123")
        ha_token = os.getenv("HA_TOKEN", "")

    ha_client = HomeAssistantClient(ha_url, ha_token)
    llm_backend = create_llm_backend(provider_name, config)
    logger.info("AI Automation Assistant started — provider=%s", provider_name)

    yield  # app runs here

    await llm_backend.close()
    await ha_client.close()
    logger.info("Shutdown complete.")


app = FastAPI(title="AI Automation Assistant", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Tool execution
# ---------------------------------------------------------------------------

async def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    """Execute a tool call and return a string result for the LLM."""
    try:
        if name == "list_entities":
            domain = arguments.get("domain")
            if domain:
                states = await ha_client.get_states()
                entities = [
                    {
                        "entity_id": s["entity_id"],
                        "name": s.get("attributes", {}).get("friendly_name", ""),
                        "state": s["state"],
                    }
                    for s in states
                    if s["entity_id"].startswith(f"{domain}.")
                ]
                return json.dumps(entities, indent=2)
            else:
                summary = await ha_client.get_entity_summary()
                return json.dumps(summary, indent=2)

        elif name == "get_entity_state":
            state = await ha_client.get_state(arguments["entity_id"])
            return json.dumps(state, indent=2)

        elif name == "call_service":
            domain = arguments["domain"]
            service = arguments["service"]
            data = dict(arguments.get("data") or {})
            if arguments.get("entity_id"):
                data["entity_id"] = arguments["entity_id"]
            await ha_client.call_service(domain, service, data)
            return f"Service {domain}.{service} called successfully."

        elif name == "create_automation":
            auto = {
                "alias": arguments["alias"],
                "description": arguments.get("description", ""),
                "trigger": arguments["trigger"],
                "condition": arguments.get("condition", []),
                "action": arguments["action"],
                "mode": arguments.get("mode", "single"),
            }
            auto_id = await ha_client.create_automation(auto)
            return (
                f"Automation '{arguments['alias']}' created with ID {auto_id}. "
                f"It's now visible in Settings → Automations & Scenes."
            )

        else:
            return f"Unknown tool: {name}"

    except Exception as e:
        logger.exception("Tool execution error (%s)", name)
        return f"Error executing {name}: {e}"


def _get_tools_for_provider() -> list[dict]:
    """Return tool definitions in the format our current LLM provider expects."""
    if provider_name == "claude":
        return tools_for_claude()
    if provider_name == "ollama":
        return tools_for_ollama()
    return tools_for_openai()


async def _build_system_prompt() -> str:
    """Build the system prompt with a live entity summary."""
    try:
        summary = await ha_client.get_entity_summary()
        lines = [f"- {count} {domain} entities" for domain, count in summary.items()]
        entity_block = "Your Home Assistant instance has:\n" + "\n".join(lines)
    except Exception:
        entity_block = "(Entity summary unavailable — HA may still be starting.)"
    return SYSTEM_PROMPT.format(entity_summary=entity_block)


# ---------------------------------------------------------------------------
# Connection manager
# ---------------------------------------------------------------------------

class ConnectionManager:
    """Manages per-client WebSocket connections and conversation history."""

    def __init__(self) -> None:
        self.active: dict[str, WebSocket] = {}
        self.history: dict[str, list[dict[str, Any]]] = {}

    async def connect(self, ws: WebSocket, client_id: str) -> None:
        await ws.accept()
        self.active[client_id] = ws
        if client_id not in self.history:
            self.history[client_id] = []

    def disconnect(self, client_id: str) -> None:
        self.active.pop(client_id, None)
        # Keep history for reconnects (pruned on next message)

    def add_message(self, client_id: str, message: dict[str, Any]) -> None:
        self.history.setdefault(client_id, []).append(message)

    def add_messages(self, client_id: str, messages: list[dict[str, Any]]) -> None:
        self.history.setdefault(client_id, []).extend(messages)

    def get_history(self, client_id: str) -> list[dict[str, Any]]:
        hist = self.history.get(client_id, [])
        # Prune old messages, keeping the most recent
        if len(hist) > MAX_HISTORY:
            hist = hist[-MAX_HISTORY:]
            self.history[client_id] = hist
        return list(hist)

    async def send(self, client_id: str, payload: dict) -> None:
        ws = self.active.get(client_id)
        if ws:
            await ws.send_json(payload)


manager = ConnectionManager()


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    logger.info("Client connected: %s", client_id)

    try:
        # Send welcome context on connect
        system_prompt = await _build_system_prompt()
        tools = _get_tools_for_provider()

        while True:
            data = await websocket.receive_json()
            user_message = data.get("message", "").strip()
            if not user_message:
                continue

            manager.add_message(client_id, {"role": "user", "content": user_message})

            try:
                history = manager.get_history(client_id)

                # Multi-turn tool-calling loop
                for round_num in range(MAX_TOOL_ROUNDS):
                    response: LLMResponse = await llm_backend.chat(
                        history, system_prompt, tools
                    )

                    if response.has_tool_calls:
                        for tc in response.tool_calls:
                            await manager.send(client_id, {
                                "type": "tool",
                                "tool": tc.name,
                                "arguments": tc.arguments,
                            })
                            result = await execute_tool(tc.name, tc.arguments)
                            # Append provider-formatted tool messages to history
                            formatted = llm_backend.format_tool_result(tc, result)
                            manager.add_messages(client_id, formatted)
                            history = manager.get_history(client_id)

                        # If there was also text alongside tool calls, send it
                        if response.content:
                            await manager.send(client_id, {
                                "type": "message",
                                "content": response.content,
                            })
                        continue  # let the LLM see the tool results

                    # Pure text response — we're done
                    if response.content:
                        manager.add_message(
                            client_id,
                            {"role": "assistant", "content": response.content},
                        )
                        await manager.send(client_id, {
                            "type": "message",
                            "content": response.content,
                        })
                    break
                else:
                    await manager.send(client_id, {
                        "type": "error",
                        "content": "Reached tool-call limit. Please try rephrasing.",
                    })

            except Exception as e:
                logger.exception("Error processing message for %s", client_id)
                await manager.send(client_id, {
                    "type": "error",
                    "content": f"Something went wrong: {e}",
                })

    except WebSocketDisconnect:
        manager.disconnect(client_id)
        logger.info("Client disconnected: %s", client_id)


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    return {"status": "ok", "provider": provider_name}


@app.get("/api/entities")
async def get_entities():
    try:
        return {"entities": await ha_client.get_states()}
    except Exception as e:
        raise HTTPException(500, detail=str(e))


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    html_file = Path(__file__).parent / "static" / "index.html"
    return HTMLResponse(html_file.read_text(encoding="utf-8"))


static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
