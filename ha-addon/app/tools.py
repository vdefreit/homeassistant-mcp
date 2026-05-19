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
        "name": "list_areas",
        "description": (
            "List all rooms/areas in the home with the entities assigned to each. "
            "Use this first for any room-based request (e.g. 'office lights', "
            "'kitchen devices') to get accurate entity IDs rather than guessing from names."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "list_entities",
        "description": (
            "List Home Assistant entities by domain. Without a domain, returns a "
            "count summary per domain. With a domain, returns all entities in that "
            "domain with their current state and friendly name."
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
        "description": "Get the detailed current state and attributes of a specific entity.",
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
            "Call a Home Assistant service to control a device. Use for turning "
            "on/off lights, toggling switches, setting thermostat temperature, "
            "playing/pausing media, and TTS announcements."
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
        "name": "list_automations",
        "description": (
            "List all existing automations with their IDs, names, and descriptions. "
            "Always call this before creating a new automation to avoid duplicates."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
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
    {
        "name": "delete_automation",
        "description": "Delete an existing automation by its ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "automation_id": {
                    "type": "string",
                    "description": "The automation ID to delete (from list_automations).",
                },
            },
            "required": ["automation_id"],
        },
    },
]


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are an AI assistant embedded in Home Assistant. You help users create \
automations, control devices, and understand their smart home.

Tools:
• list_areas – get rooms and their entities (use first for ANY room-based request)
• list_entities – browse devices by domain (light, switch, sensor, etc.)
• get_entity_state – check current state of a specific device
• call_service – control devices (turn on/off, adjust settings, TTS)
• list_automations – see existing automations (always check before creating)
• create_automation – create automations visible in HA Settings → Automations
• delete_automation – remove an automation by ID

Rules:
1. For room/area requests, call list_areas first — never guess entity IDs from names.
2. Before creating an automation, call list_automations to avoid duplicates.
3. Use exact entity IDs from tool results — never invent them.
4. Confirm what you did after every action.

Automation format examples:
Trigger — time: {{"platform": "time", "at": "22:00:00"}}
Trigger — state: {{"platform": "state", "entity_id": "binary_sensor.door", "to": "on"}}
Trigger — sunset: {{"platform": "sun", "event": "sunset", "offset": "+00:30:00"}}
Trigger — time pattern: {{"platform": "time_pattern", "minutes": "/30"}}
Action — service: {{"service": "light.turn_off", "target": {{"entity_id": "light.office"}}}}
Action — TTS: {{"service": "tts.cloud_say", "target": {{"entity_id": "media_player.kitchen"}}, "data": {{"message": "Hello!"}}}}
Action — delay: {{"delay": {{"seconds": 30}}}}
Condition — person home: {{"condition": "state", "entity_id": "person.vince", "state": "home"}}
Condition — time: {{"condition": "time", "after": "22:00:00", "before": "08:00:00"}}

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
