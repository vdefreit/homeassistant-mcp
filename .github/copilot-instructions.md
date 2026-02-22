- [x] Verify that the copilot-instructions.md file in the .github directory is created.

- [x] Clarify Project Requirements

- [x] Scaffold the Project

- [x] Customize the Project

- [x] Install Required Extensions

- [x] Compile the Project

- [x] Create and Run Task

- [x] Launch the Project

- [x] Ensure Documentation is Complete

## Project: Home Assistant MCP Server + AI Automation Add-on
- Type: Model Context Protocol (MCP) Server + HA Supervisor Add-on
- Language: Python 3.11+
- Purpose: Connect to Home Assistant instance and expose entities/services via MCP,
  plus a web-based chat add-on with LLM tool-calling for automation creation
- MCP SDK: Official MCP Python SDK (mcp>=1.0.0)
- Add-on stack: FastAPI, WebSocket, OpenAI/Claude/Ollama with native tool calling
- Documentation: https://github.com/modelcontextprotocol/python-sdk

## Quick Start — MCP Server
1. Configure `.env` file with HA_URL and HA_TOKEN
2. Run: `python server.py` to test
3. Add to Claude Desktop config for MCP integration

## Quick Start — HA Add-on
1. Add GitHub repo as custom HA add-on repository
2. Install, configure LLM provider + API key
3. Start add-on, open Web UI from sidebar
