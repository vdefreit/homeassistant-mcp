# AI Automation Assistant — Home Assistant Add-on

Create and manage Home Assistant automations by chatting in plain English.

## What it does

This add-on gives you a chat interface inside Home Assistant where you can
describe automations in natural language and the AI creates them for you.
The AI can also list your devices, check their states, and control them
directly — all through conversation.

Under the hood, the AI has **tool-calling** access to your HA instance:
it can browse entities, call services, and write automations to your
`automations.yaml` so they appear immediately in the HA UI.

### Supported LLM Providers

| Provider | Cost | Latency | Tool Calling | Notes |
|----------|------|---------|--------------|-------|
| **OpenAI** (GPT-4o-mini) | ~$0.50–5/mo | Fast | Native | Best starting point |
| **OpenAI** (GPT-4o) | ~$2–15/mo | Medium | Native | Highest quality |
| **Claude** (claude-sonnet-4-20250514) | ~$1–10/mo | Medium | Native | Great reasoning |
| **Ollama** (llama3, mistral) | Free | Varies | Model-dependent | Runs locally |

## Setup

### 1. Install

**From GitHub repo:**
1. Go to **Settings → Add-ons → Add-on Store → ⋮ → Repositories**
2. Add: `https://github.com/vdefreit/homeassistant-mcp`
3. Refresh, find **AI Automation Assistant**, click **Install**

**Manual:**
Copy the `ha-addon/` folder to your HA config's `addons/` directory and
reload add-ons.

### 2. Configure

Go to the add-on's **Configuration** tab and set:

```yaml
llm_provider: openai          # or: claude, ollama
openai_api_key: sk-...        # your OpenAI key
openai_model: gpt-4o-mini     # or gpt-4o
```

For Claude:
```yaml
llm_provider: claude
claude_api_key: sk-ant-...
claude_model: claude-sonnet-4-20250514
```

For Ollama (free, local):
```yaml
llm_provider: ollama
ollama_url: http://YOUR_OLLAMA_IP:11434
ollama_model: llama3
```

### 3. Start

Click **Start**, then **Open Web UI** (or find it in the sidebar as
"AI Automations").

## Example Conversations

> **You:** List all my lights  
> *AI browses your entities and shows every light with its current state*

> **You:** Create an automation to turn off the living room lights at midnight  
> *AI creates the automation and confirms it's visible in Settings → Automations*

> **You:** When I arrive home after sunset, flash the porch light 5 times  
> *AI asks which presence entity to use, then builds a proper trigger/action*

> **You:** Turn on the kitchen lights to 50% brightness  
> *AI directly calls the light.turn_on service*

## Architecture

```
┌──────────────┐    WebSocket    ┌──────────────────────┐
│   Browser    │ ◄─────────────► │  FastAPI Server      │
│  (index.html)│                 │                      │
└──────────────┘                 │  ┌────────────────┐  │
                                 │  │  LLM Backend   │  │
                                 │  │ (OpenAI/Claude │  │
                                 │  │  /Ollama)      │  │
                                 │  └───────┬────────┘  │
                                 │          │ tool calls │
                                 │  ┌───────▼────────┐  │
                                 │  │  HA Client     │──┼──► Home Assistant API
                                 │  │  (REST + YAML) │  │
                                 │  └────────────────┘  │
                                 └──────────────────────┘
```

**Tool-calling flow:**
1. You send a message via WebSocket
2. Server sends your message + tool definitions to the LLM
3. LLM decides to call tools (list entities, create automation, etc.)
4. Server executes tools against HA, feeds results back to LLM
5. LLM generates a final human-readable response
6. Response sent back to you via WebSocket

## Troubleshooting

**Add-on won't start**
- Check logs for API key errors
- Verify the correct provider is selected

**"Disconnected" in the UI**
- Refresh the page
- Check add-on logs for crash info
- Ensure the add-on is running (green indicator)

**AI can't find my devices**
- The AI uses `list_entities` to discover devices — try asking it to list
  a specific domain
- Check that `homeassistant_api: true` is in config.yaml

**Automations not appearing**
- Check HA logs (Settings → System → Logs)
- Try manually reloading: Developer Tools → YAML → Automations
- Verify `/config/automations.yaml` is writable

**Ollama not connecting**
- Confirm Ollama server is running: `curl http://IP:11434`
- Check firewall rules
- Use a tool-capable model (llama3, mistral) for best results

## Privacy

- Conversations go to your chosen LLM provider (OpenAI / Anthropic)
- For maximum privacy, use Ollama — everything stays local
- API keys are stored in HA's protected add-on configuration
- No telemetry or data collection by this add-on
