#!/usr/bin/env python3
"""
Home Assistant MCP Server

Connects to a Home Assistant instance and exposes entities/services via MCP protocol.
"""

import asyncio
import os
import json
import yaml
from pathlib import Path
from typing import Any, Optional
from dotenv import load_dotenv
import httpx
from mcp.server import Server
from mcp.types import (
    Tool,
    TextContent,
    Resource,
    CallToolRequest,
    ListResourcesRequest,
    ListToolsRequest,
    ReadResourceRequest,
)
import mcp.server.stdio

# Load environment variables from .env file
load_dotenv()

HA_URL = os.getenv("HA_URL", "http://localhost:8123")
HA_TOKEN = os.getenv("HA_TOKEN")
HA_AUTOMATIONS_PATH = os.getenv("HA_AUTOMATIONS_PATH", "Z:\\automations.yaml")

if not HA_TOKEN:
    raise ValueError("HA_TOKEN environment variable is required")

# Remove trailing slash from URL
HA_URL = HA_URL.rstrip("/")


class HomeAssistantClient:
    """Client for interacting with Home Assistant API."""
    
    def __init__(self, url: str, token: str):
        self.url = url
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
    
    async def call_api(
        self, 
        endpoint: str, 
        method: str = "GET", 
        data: Optional[dict] = None
    ) -> Any:
        """Make an API call to Home Assistant."""
        url = f"{self.url}/api/{endpoint}"
        
        async with httpx.AsyncClient() as client:
            try:
                if method == "GET":
                    response = await client.get(url, headers=self.headers, timeout=10.0)
                elif method == "POST":
                    response = await client.post(
                        url, 
                        headers=self.headers, 
                        json=data,
                        timeout=10.0
                    )
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                response.raise_for_status()
                return response.json()
            
            except httpx.HTTPError as e:
                raise Exception(f"Home Assistant API error: {str(e)}")
    
    async def get_states(self) -> list[dict]:
        """Get all entity states."""
        return await self.call_api("states")
    
    async def get_state(self, entity_id: str) -> dict:
        """Get state of a specific entity."""
        return await self.call_api(f"states/{entity_id}")
    
    async def get_services(self) -> list[dict]:
        """Get all available services."""
        return await self.call_api("services")
    
    async def call_service(
        self, 
        domain: str, 
        service: str, 
        service_data: Optional[dict] = None
    ) -> list[dict]:
        """Call a Home Assistant service."""
        return await self.call_api(
            f"services/{domain}/{service}",
            method="POST",
            data=service_data or {}
        )
    
    async def get_automations(self) -> list[dict]:
        """Get all automations."""
        return await self.call_api("config/automation/config")
    
    async def create_automation(self, automation: dict) -> dict:
        """Create a new automation."""
        return await self.call_api(
            "config/automation/config",
            method="POST",
            data=automation
        )
    
    async def update_automation(self, automation_id: str, automation: dict) -> dict:
        """Update an existing automation."""
        return await self.call_api(
            f"config/automation/config/{automation_id}",
            method="PUT",
            data=automation
        )
    
    async def delete_automation(self, automation_id: str) -> dict:
        """Delete an automation."""
        return await self.call_api(
            f"config/automation/config/{automation_id}",
            method="DELETE"
        )
    
    async def reload_automations(self) -> dict:
        """Reload automations from YAML files."""
        return await self.call_api(
            "services/automation/reload",
            method="POST"
        )


def write_automation_to_yaml(automation: dict, file_path: str) -> None:
    """Write automation to YAML file."""
    # Read existing automations
    automations = []
    if Path(file_path).exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if content.strip():
                automations = yaml.safe_load(content) or []
    
    # Ensure it's a list
    if not isinstance(automations, list):
        automations = [automations] if automations else []
    
    # Add new automation with a unique ID
    import time
    automation['id'] = f"mcp_{int(time.time())}"
    automations.append(automation)
    
    # Write back to file
    with open(file_path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(automations, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    return automation['id']


# Initialize Home Assistant client
ha_client = HomeAssistantClient(HA_URL, HA_TOKEN)

# Create MCP server
app = Server("homeassistant-mcp-server")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="get_state",
            description="Get the current state of a Home Assistant entity",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "The entity ID (e.g., light.living_room, sensor.temperature)",
                    }
                },
                "required": ["entity_id"],
            },
        ),
        Tool(
            name="call_service",
            description="Call a Home Assistant service to control devices",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "Service domain (e.g., light, switch, climate)",
                    },
                    "service": {
                        "type": "string",
                        "description": "Service name (e.g., turn_on, turn_off, set_temperature)",
                    },
                    "entity_id": {
                        "type": "string",
                        "description": "Target entity ID (optional)",
                    },
                    "service_data": {
                        "type": "object",
                        "description": "Additional service parameters (e.g., brightness, temperature)",
                    },
                },
                "required": ["domain", "service"],
            },
        ),
        Tool(
            name="list_entities",
            description="List all entities, optionally filtered by domain",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "Filter by domain (e.g., light, switch, sensor)",
                    }
                },
            },
        ),
        Tool(
            name="create_automation",
            description="Create a new Home Assistant automation that will appear in the HA UI",
            inputSchema={
                "type": "object",
                "properties": {
                    "alias": {
                        "type": "string",
                        "description": "Friendly name for the automation",
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of what the automation does",
                    },
                    "trigger": {
                        "type": "array",
                        "description": "List of triggers (e.g., time, state change, event)",
                    },
                    "condition": {
                        "type": "array",
                        "description": "Optional conditions that must be met",
                    },
                    "action": {
                        "type": "array",
                        "description": "Actions to perform when triggered",
                    },
                    "mode": {
                        "type": "string",
                        "description": "Execution mode: single, restart, queued, or parallel (default: single)",
                    },
                },
                "required": ["alias", "trigger", "action"],
            },
        ),
        Tool(
            name="list_automations",
            description="List all existing Home Assistant automations",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="delete_automation",
            description="Delete an existing automation by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "automation_id": {
                        "type": "string",
                        "description": "The automation ID to delete",
                    }
                },
                "required": ["automation_id"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "get_state":
            entity_id = arguments.get("entity_id")
            state = await ha_client.get_state(entity_id)
            return [TextContent(type="text", text=json.dumps(state, indent=2))]
        
        elif name == "call_service":
            domain = arguments.get("domain")
            service = arguments.get("service")
            entity_id = arguments.get("entity_id")
            service_data = arguments.get("service_data", {})
            
            # Add entity_id to service data if provided
            if entity_id:
                service_data["entity_id"] = entity_id
            
            result = await ha_client.call_service(domain, service, service_data)
            return [
                TextContent(
                    type="text",
                    text=f"Service called successfully\n{json.dumps(result, indent=2)}"
                )
            ]
        
        elif name == "list_entities":
            domain = arguments.get("domain")
            states = await ha_client.get_states()
            
            # Filter by domain if specified
            if domain:
                states = [s for s in states if s["entity_id"].startswith(f"{domain}.")]
            
            # Create a simplified list
            entities = [
                {
                    "entity_id": state["entity_id"],
                    "state": state["state"],
                    "friendly_name": state.get("attributes", {}).get("friendly_name"),
                }
                for state in states
            ]
            
            return [TextContent(type="text", text=json.dumps(entities, indent=2))]
        
        elif name == "create_automation":
            automation_config = {
                "alias": arguments.get("alias"),
                "description": arguments.get("description", ""),
                "trigger": arguments.get("trigger"),
                "condition": arguments.get("condition", []),
                "action": arguments.get("action"),
                "mode": arguments.get("mode", "single"),
            }
            
            # Write to YAML file
            automation_id = write_automation_to_yaml(automation_config, HA_AUTOMATIONS_PATH)
            
            # Reload automations
            await ha_client.reload_automations()
            
            return [
                TextContent(
                    type="text",
                    text=f"✓ Automation created successfully!\n\nID: {automation_id}\nName: {automation_config['alias']}\n\nThe automation has been written to automations.yaml and loaded into Home Assistant.\nYou can now see and edit it in: Settings → Automations & Scenes"
                )
            ]
        
        elif name == "list_automations":
            automations = await ha_client.get_automations()
            
            # Create a simplified list
            automation_list = [
                {
                    "id": auto.get("id"),
                    "alias": auto.get("alias"),
                    "description": auto.get("description", ""),
                }
                for auto in automations
            ]
            
            return [TextContent(type="text", text=json.dumps(automation_list, indent=2))]
        
        elif name == "delete_automation":
            automation_id = arguments.get("automation_id")
            result = await ha_client.delete_automation(automation_id)
            return [
                TextContent(
                    type="text",
                    text=f"✓ Automation deleted successfully: {automation_id}"
                )
            ]
        
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


@app.list_resources()
async def list_resources() -> list[Resource]:
    """List available resources."""
    return [
        Resource(
            uri="ha://states",
            name="All Entity States",
            mimeType="application/json",
            description="Get all entity states from Home Assistant",
        ),
        Resource(
            uri="ha://services",
            name="Available Services",
            mimeType="application/json",
            description="Get all available Home Assistant services",
        ),
    ]


@app.read_resource()
async def read_resource(uri: str) -> str:
    """Read a resource."""
    if uri == "ha://states":
        states = await ha_client.get_states()
        return json.dumps(states, indent=2)
    
    elif uri == "ha://services":
        services = await ha_client.get_services()
        return json.dumps(services, indent=2)
    
    else:
        raise ValueError(f"Unknown resource: {uri}")


async def main():
    """Run the MCP server."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
