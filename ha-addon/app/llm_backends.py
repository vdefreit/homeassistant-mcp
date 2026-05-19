"""
LLM backend abstraction layer with native tool-calling support.

Each backend wraps a provider SDK and exposes a unified interface that
returns either text or tool-call requests. The main server loop handles
tool execution and feeds results back in for multi-turn tool use.

Supports: OpenAI, Anthropic Claude, Ollama (OpenAI-compatible chat API).
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Unified response types
# ---------------------------------------------------------------------------

@dataclass
class ToolCall:
    """A single tool invocation requested by the LLM."""
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    """Unified response from any LLM backend."""
    content: Optional[str] = None
    tool_calls: list[ToolCall] = field(default_factory=list)

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class LLMBackend(ABC):
    """Abstract base for LLM providers."""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, Any]],
        system_prompt: str,
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        """Send a conversation and return text and/or tool calls."""

    @abstractmethod
    def format_tool_result(
        self,
        tool_call: ToolCall,
        result: str,
    ) -> list[dict[str, Any]]:
        """Return message(s) to append to history after a tool executes.

        Different providers need tool results in different shapes:
        - OpenAI: assistant message with tool_calls + tool message per result
        - Claude: assistant message with tool_use blocks + user message with
          tool_result blocks
        - Ollama: same as OpenAI
        """

    async def close(self) -> None:
        """Release any held resources (override if needed)."""


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------

class OpenAIBackend(LLMBackend):
    """OpenAI-compatible backend. Supports real OpenAI and local servers like LM Studio."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", base_url: str | None = None) -> None:
        from openai import AsyncOpenAI
        self.model = model
        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url.rstrip("/") + "/v1" if not base_url.rstrip("/").endswith("/v1") else base_url
        self._client = AsyncOpenAI(**kwargs)

    async def chat(self, messages, system_prompt, tools=None):
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "system", "content": system_prompt}, *messages],
            "temperature": 0.7,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        resp = await self._client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message

        tool_calls = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                tool_calls.append(ToolCall(id=tc.id, name=tc.function.name, arguments=args))

        return LLMResponse(content=msg.content, tool_calls=tool_calls)

    def format_tool_result(self, tool_call, result):
        """OpenAI expects the assistant's tool_calls echoed, then a tool message."""
        return [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.name,
                            "arguments": json.dumps(tool_call.arguments),
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            },
        ]

    async def close(self):
        await self._client.close()


# ---------------------------------------------------------------------------
# Anthropic Claude
# ---------------------------------------------------------------------------

class ClaudeBackend(LLMBackend):
    """Anthropic Claude backend using the official SDK."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514") -> None:
        from anthropic import AsyncAnthropic
        self.model = model
        self._client = AsyncAnthropic(api_key=api_key)

    async def chat(self, messages, system_prompt, tools=None):
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": messages,
            "temperature": 0.7,
        }
        if tools:
            kwargs["tools"] = tools

        resp = await self._client.messages.create(**kwargs)

        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in resp.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(id=block.id, name=block.name, arguments=block.input)
                )

        content = "\n".join(text_parts) if text_parts else None
        return LLMResponse(content=content, tool_calls=tool_calls)

    def format_tool_result(self, tool_call, result):
        """Claude expects tool_use in assistant content, tool_result in a user message."""
        return [
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": tool_call.id,
                        "name": tool_call.name,
                        "input": tool_call.arguments,
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_call.id,
                        "content": result,
                    }
                ],
            },
        ]

    async def close(self):
        await self._client.close()


# ---------------------------------------------------------------------------
# Ollama (local)
# ---------------------------------------------------------------------------

class OllamaBackend(LLMBackend):
    """Local Ollama backend using the /api/chat endpoint (OpenAI-compatible tool format)."""

    def __init__(self, url: str = "http://localhost:11434", model: str = "llama3") -> None:
        self.model = model
        self._client = httpx.AsyncClient(
            base_url=url.rstrip("/"),
            timeout=httpx.Timeout(120.0, connect=10.0),
        )

    async def chat(self, messages, system_prompt, tools=None):
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "system", "content": system_prompt}, *messages],
            "stream": False,
        }
        if tools:
            payload["tools"] = tools

        resp = await self._client.post("/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()
        msg = data.get("message", {})

        tool_calls: list[ToolCall] = []
        if msg.get("tool_calls"):
            for i, tc in enumerate(msg["tool_calls"]):
                func = tc.get("function", {})
                args = func.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                tool_calls.append(
                    ToolCall(
                        id=f"ollama_{i}",
                        name=func.get("name", ""),
                        arguments=args,
                    )
                )

        return LLMResponse(content=msg.get("content"), tool_calls=tool_calls)

    def format_tool_result(self, tool_call, result):
        """Ollama uses the same format as OpenAI."""
        return [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.name,
                            "arguments": json.dumps(tool_call.arguments),
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            },
        ]

    async def close(self):
        await self._client.aclose()


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_llm_backend(provider: str, config: dict[str, Any]) -> LLMBackend:
    """Instantiate the appropriate backend from add-on configuration."""
    provider = provider.lower().strip()

    if provider == "openai":
        api_key = config.get("openai_api_key", "").strip()
        base_url = config.get("openai_base_url", "").strip() or None
        if not api_key and not base_url:
            raise ValueError("OpenAI provider selected but no API key provided.")
        # LM Studio / local servers don't need a real key; use a placeholder if empty
        effective_key = api_key or "lm-studio"
        return OpenAIBackend(effective_key, config.get("openai_model", "gpt-4o-mini"), base_url)

    if provider == "claude":
        api_key = config.get("claude_api_key", "").strip()
        if not api_key:
            raise ValueError("Claude provider selected but no API key provided.")
        return ClaudeBackend(api_key, config.get("claude_model", "claude-sonnet-4-20250514"))

    if provider == "ollama":
        url = config.get("ollama_url", "http://localhost:11434")
        model = config.get("ollama_model", "llama3")
        return OllamaBackend(url, model)

    raise ValueError(f"Unknown LLM provider: '{provider}'")
