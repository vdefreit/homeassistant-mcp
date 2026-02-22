# Home Assistant MCP + AI Automation Assistant

Two ways to manage your Home Assistant with AI:

1. **MCP Server** (`server.py`) — Use from VS Code / Claude Desktop via the
   Model Context Protocol to query entities, call services, and create
   automations through your IDE.

2. **HA Add-on** (`ha-addon/`) — A self-contained Home Assistant add-on with
   a chat UI. Accessible from any device via the HA mobile app or browser.
   The AI has full tool-calling access to list entities, control devices, and
   create automations that appear immediately in the HA UI.

## Quick Start — MCP Server

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure .env
cp .env.example .env
# Edit .env with your HA_URL and HA_TOKEN

# 3. Run
python server.py
```

See [Claude Desktop config](#claude-desktop) below for IDE integration.

## Quick Start — HA Add-on

1. In HA: **Settings → Add-ons → Add-on Store → ⋮ → Repositories**
2. Add `https://github.com/vdefreit/homeassistant-mcp`
3. Install **AI Automation Assistant**, configure your LLM API key, start it
4. Open the Web UI from the sidebar

Full details in [ha-addon/README.md](ha-addon/README.md).

## Project Structure

```
├── server.py              # MCP server (VS Code / Claude Desktop)
├── home_status.py         # Quick home status dashboard
├── ha-addon/              # Home Assistant add-on
│   ├── config.yaml        # Add-on manifest
│   ├── Dockerfile
│   ├── app/
│   │   ├── main.py        # FastAPI + WebSocket server
│   │   ├── llm_backends.py # OpenAI / Claude / Ollama with tool calling
│   │   ├── ha_client.py   # HA REST API + YAML automation management
│   │   ├── tools.py       # Tool definitions for LLM function calling
│   │   └── static/
│   │       └── index.html # Chat UI
│   └── run.sh
├── scripts/               # Utility & test scripts
├── repository.json        # HA add-on repository manifest
└── .env.example           # Environment template
```

## Prerequisites

- Python 3.11+
- Home Assistant with API access
- Long-Lived Access Token (Profile → Security → Long-Lived Access Tokens)

## Claude Desktop

Add to `%APPDATA%\Claude\claude_desktop_config.json` (Windows) or
`~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "homeassistant": {
      "command": "python",
      "args": ["PATH_TO/server.py"],
      "env": {
        "HA_URL": "http://YOUR_HA_IP:8123",
        "HA_TOKEN": "YOUR_TOKEN"
      }
    }
  }
}
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `get_state` | Get current state of any entity |
| `call_service` | Control devices (lights, switches, climate, etc.) |
| `list_entities` | List entities, optionally filtered by domain |
| `create_automation` | Create automations that appear in HA UI |
| `list_automations` | List existing automations |
| `delete_automation` | Remove an automation by ID |

## License

MIT
