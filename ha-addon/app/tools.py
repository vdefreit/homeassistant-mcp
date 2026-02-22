"""
Tool definitions for the AI Automation Assistant.

Defines the tools the LLM can invoke to interact with Home Assistant,
along with format converters for each LLM provider.
"""

from typing import Any

# ---------------------------------------------------------------------------
# Universal tool definitions (provider-agnostic)
# ---------------------------------------------------------------------------

TOOLS: list[dict[str, Any]] = [
    {
        "name": "list_entities",
        "description": (
            "List Home Assistant entities. Without a domain filter, returns a "
            "summary of entity counts per domain. With a domain filter, returns "
            "all entities in that domain with their current state."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": (
                        "Entity domain to filter by (e.g. 'light', 'switch', "
                        "'sensor', 'climate', 'automation', 'person', 'media_player'). "
                        "Omit to get a count summary of all domains."
                    ),
                },
            },
        },
    },
    {
        "name": "get_entity_state",
        "description": (
            "Get the detailed current state and attributes of a specific entity."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "The entity ID (e.g. 'light.living_room', 'switch.porch_light').",
                },
            },
            "required": ["entity_id"],
        },
    },
    {
        "name": "call_service",
        "description": (
            "Call a Home Assistant service to control a device. Examples: "
            "turn on/off lights, toggle switches, set thermostat temperature, "
            "play/pause media, send TTS announcements."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Service domain (e.g. 'light', 'switch', 'climate', 'tts').",
                },
                "service": {
                    "type": "string",
                    "description": "Service name (e.g. 'turn_on', 'turn_off', 'toggle', 'cloud_say').",
                },
                "entity_id": {
                    "type": "string",
                    "description": "Target entity ID (optional for some services).",
                },
                "data": {
                    "type": "object",
                    "description": (
                        "Additional service data, e.g. "
                        "{'brightness': 255, 'rgb_color': [255, 0, 0]} for lights, "
                        "{'message': 'Hello'} for TTS."
                    ),
                },
            },
            "required": ["domain", "service"],
        },
    },
    {
        "name": "create_automation",
        "description": (
            "Create a new Home Assistant automation that will appear in the HA UI "
            "under Settings → Automations & Scenes. Use proper HA trigger, "
            "condition, and action structures."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "alias": {
                    "type": "string",
                    "description": "Human-friendly name for the automation.",
                },
                "description": {
                    "type": "string",
                    "description": "Description of what the automation does.",
                },
                "trigger": {
                    "type": "array",
                    "description": "List of trigger configurations.",
                    "items": {"type": "object"},
                },
                "condition": {
                    "type": "array",
                    "description": "Optional list of conditions that must be met.",
                    "items": {"type": "object"},
                },
                "action": {
                    "type": "array",
                    "description": "List of actions to perform when triggered.",
                    "items": {"type": "object"},
                },
                "mode": {
                    "type": "string",
                    "enum": ["single", "restart", "queued", "parallel"],
                    "description": "Automation execution mode (default: single).",
                },
            },
            "required": ["alias", "trigger", "action"],
        },
    },
]


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are an AI assistant embedded in Home Assistant. You help users create \
automations, control devices, and understand their smart home.

You have tools to interact with Home Assistant:
• list_entities – browse available devices and entities
• get_entity_state – check the current state of any device
• call_service – control devices (turn on/off, adjust settings, play TTS)
• create_automation – create automations that appear in the HA UI

Guidelines:
1. When a user asks to create an automation, first use list_entities to find \
   the correct entity IDs. Don't guess entity names.
2. Ask clarifying questions if the request is ambiguous (timing, conditions, \
   specific devices).
3. Use proper Home Assistant automation YAML structure for triggers, \
   conditions, and actions.
4. After creating or controlling something, confirm what you did.
5. Be conversational and helpful.

Common trigger platforms: state, time, time_pattern, sun, event, zone, \
numeric_state, template, device
Common service domains: light, switch, climate, media_player, automation, \
scene, script, notify, tts
Common conditions: state, time, sun, zone, numeric_state, template

{entity_summary}\
"""


# ---------------------------------------------------------------------------
# Provider-specific format converters
# ---------------------------------------------------------------------------

def tools_for_openai() -> list[dict]:
    """Convert to OpenAI function-calling format."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["parameters"],
            },
        }
        for t in TOOLS
    ]


def tools_for_claude() -> list[dict]:
    """Convert to Anthropic Claude tool-use format."""
    return [
        {
            "name": t["name"],
            "description": t["description"],
            "input_schema": t["parameters"],
        }
        for t in TOOLS
    ]


def tools_for_ollama() -> list[dict]:
    """Convert to Ollama format (OpenAI-compatible)."""
    return tools_for_openai()
