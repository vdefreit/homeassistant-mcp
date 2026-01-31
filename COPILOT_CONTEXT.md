# Home Assistant MCP Server - Project Context

## Overview
This is a Model Context Protocol (MCP) server that connects VS Code to a Home Assistant instance, enabling conversational automation creation that appears in the Home Assistant UI.

## Environment Setup
- **Home Assistant URL**: Stored in `.env` as `HA_URL` (http://192.168.0.59:8123)
- **Authentication**: Long-lived access token in `.env` as `HA_TOKEN`
- **File Access**: Direct write to `Z:\automations.yaml` via Samba share
- **Credentials**: Samba username `homeassistant`, password in `.env` as needed

## Key Files

### Core
- `server.py` - Main MCP server with Home Assistant integration
- `.env` - Secrets (NOT in git, create manually on new machines)
- `.env.example` - Template for environment variables
- `requirements.txt` - Python dependencies (mcp, httpx, python-dotenv, pyyaml)

### Utilities
- `test_connection.py` - Verify Home Assistant API connectivity
- `list_lights.py` - List all light entities
- `verify_lauren_automation.py` - Check automation status
- `test_final_show.py` - Test Lauren's Grand Entrance sequence

### Automation Management
- `update_shorter_show.py` - Script that creates Lauren's Grand Entrance automation

## How Automations Work

### Creating Automations
1. Automations are written directly to `Z:\automations.yaml` via `write_automation_to_yaml()`
2. Each automation gets a unique ID: `mcp_{timestamp}`
3. After writing, call `automation.reload` service to load into HA
4. Automations immediately appear in HA UI: Settings → Automations & Scenes

### Automation Structure
```python
automation = {
    'id': f"mcp_{int(time.time())}",
    'alias': "Human-readable name",
    'description': "What it does",
    'trigger': [...],  # When to run
    'condition': [...],  # Optional checks
    'action': [...],  # What to do
    'mode': 'single'  # Execution mode
}
```

## Important Entities

### People
- `person.lauren_cahill` - Lauren's presence tracker

### Lights (31 total)
- `light.gaming_lightstrip` - Gaming PC light strip
- `light.hue_play_1` - Gaming monitor lightbar
- `light.office_potlights` - Office pot lights
- `switch.porch_light` - Front porch light (used in Lauren's automation)

### Media Players
- `media_player.nestmini1497` - Kitchen speaker (used for TTS)

### Sensors
- `event.front_door_motion` - Front door motion detection
- `event.front_door_chime` - Doorbell press

## Current Automations

### Lauren's Grand Entrance
**Purpose**: Welcome Lauren home after sunset with light show and announcement

**Trigger**: Front door motion detected (`event.front_door_motion`)

**Conditions**:
- `person.lauren_cahill` state is "home"
- Current time is after sunset

**Actions**:
1. Plays TTS message 5 times via kitchen speaker
2. Flashes porch light 6 times per message (30 total)
3. Message: "Welcome home Lauren! The robots have gained sentience..."
4. Total duration: ~25-30 seconds

## TTS Configuration
- **Service**: `tts.cloud_say` (Home Assistant Cloud TTS)
- **Reason**: Google Nest devices need to be "on" or will auto-wake with cloud service
- **Target**: `media_player.nestmini1497` (Kitchen speaker)

## Voice Control Integration
- **Method**: "Tell Home Assistant to [command]" via Google Gemini
- **Example**: "Tell Home Assistant to turn on office lights"
- Gemini routes commands to HA instead of responding as LLM

## Network Access
- **Samba Share**: `\\192.168.0.59\config` mapped to `Z:`
- **Direct File Write**: Enables instant automation creation without API limitations
- **Latency**: ~2 seconds (write + reload)

## Common Patterns

### Creating a New Automation
```python
# 1. Build automation config
automation = {
    'id': f"mcp_{int(time.time())}",
    'alias': "Name",
    'trigger': [...],
    'action': [...]
}

# 2. Write to YAML
write_automation_to_yaml(automation, HA_AUTOMATIONS_PATH)

# 3. Reload
await ha_client.reload_automations()
```

### Testing Automations
1. Create test script that calls services directly
2. Bypass conditions for testing
3. Use shorter sequences for quick iteration
4. Always verify in HA UI after creation

### Light Control
```python
# Turn on with RGB color
{'service': 'light.turn_on', 'target': {'entity_id': 'light.name'}, 'data': {'rgb_color': [255, 0, 0], 'brightness': 255}}

# Toggle switch
{'service': 'switch.toggle', 'target': {'entity_id': 'switch.name'}}
```

### TTS Announcements
```python
{
    'service': 'tts.cloud_say',
    'target': {'entity_id': 'media_player.nestmini1497'},
    'data': {'message': "Your message here"}
}
```

## Troubleshooting

### Automation Not Triggering
- Check entity states in HA
- Verify conditions are met (time, state, etc.)
- Check HA logs for errors
- Use `verify_lauren_automation.py` to check status

### TTS Not Playing
- Ensure speaker entity is available (not "unavailable")
- Use `tts.cloud_say` not `tts.google_translate_say`
- Check HA Cloud subscription is active
- Test with `test_cloud_tts.py`

### File Access Issues
- Verify Z: drive is mapped
- Check Samba credentials
- Ensure automations.yaml is writable
- Test with direct file operations

## Future Enhancements
- More voice-triggered automations
- Scene creation for different moods
- Time-based automations (morning, night)
- Location-based triggers
- Multi-room audio announcements

## Security Notes
- `.env` contains sensitive tokens - NEVER commit to git
- `.gitignore` protects secrets, virtual environment, and automations
- Long-lived tokens should be rotated periodically
- Samba credentials stored in environment variables
