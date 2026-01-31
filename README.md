# Home Assistant MCP Server

A Model Context Protocol (MCP) server that connects to your Home Assistant instance, allowing you to query and control your smart home devices through Claude Desktop or other MCP clients.

## Features

- **Get Entity States**: Query the current state of any Home Assistant entity
- **Call Services**: Control devices (turn lights on/off, adjust thermostats, etc.)
- **List Entities**: Browse all entities or filter by domain (lights, switches, sensors, etc.)
- **Resources**: Access all states and available services as MCP resources

## Prerequisites

- Python 3.10 or higher
- Home Assistant instance with API access
- Home Assistant Long-Lived Access Token

## Setup

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Home Assistant Connection

Create a `.env` file in the project root:

```bash
HA_URL=http://your-homeassistant-ip:8123
HA_TOKEN=your_long_lived_access_token
```

To create a Long-Lived Access Token:
1. Open Home Assistant
2. Click your profile (bottom left)
3. Scroll to "Long-Lived Access Tokens"
4. Click "Create Token"
5. Copy the token to your `.env` file

### 3. Test the Server

Run the server directly:

```bash
python server.py
```

## Usage with Claude Desktop

Add this to your Claude Desktop configuration file:

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "homeassistant": {
      "command": "python",
      "args": [
        "C:\\Users\\vince\\Home Assistant MCP\\server.py"
      ],
      "env": {
        "HA_URL": "http://your-homeassistant-ip:8123",
        "HA_TOKEN": "your_token_here"
      }
    }
  }
}
```

**Important**: Use absolute paths and update the path to match your installation location.

## Available Tools

### get_state
Get the current state of an entity:
```
Get the state of light.living_room
```

### call_service
Control devices:
```
Turn on the living room light
Call service light.turn_on for light.living_room with brightness 255
```

### list_entities
List all entities or filter by domain:
```
List all light entities
Show me all sensors
```

## Available Resources

- `ha://states` - All entity states
- `ha://services` - All available services

## Troubleshooting

**Connection errors**: Verify your HA_URL is correct and Home Assistant is accessible
**Authentication errors**: Check that your HA_TOKEN is valid and hasn't expired
**Python not found**: Ensure Python 3.10+ is installed and in your PATH

## Development

Run with debug output:
```bash
python server.py
```

The server uses stdio transport and logs to stderr, so you'll see connection messages when clients connect.

## License

MIT
