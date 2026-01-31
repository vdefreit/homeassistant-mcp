#!/usr/bin/env python3
"""
List all light entities from Home Assistant
"""

import asyncio
import os
from dotenv import load_dotenv
import httpx

load_dotenv()

HA_URL = os.getenv("HA_URL", "").rstrip("/")
HA_TOKEN = os.getenv("HA_TOKEN", "")

async def list_lights():
    """List all light entities."""
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{HA_URL}/api/states", headers=headers, timeout=10.0)
            response.raise_for_status()
            states = response.json()
            
            # Filter for light entities
            lights = [s for s in states if s["entity_id"].startswith("light.")]
            
            print(f"Found {len(lights)} lights:\n")
            
            for light in lights:
                entity_id = light["entity_id"]
                state = light["state"]
                friendly_name = light.get("attributes", {}).get("friendly_name", "N/A")
                brightness = light.get("attributes", {}).get("brightness", "N/A")
                
                status = "🟡 ON" if state == "on" else "⚫ OFF"
                bright_info = f" (brightness: {brightness})" if state == "on" and brightness != "N/A" else ""
                
                print(f"{status} {friendly_name}")
                print(f"    ID: {entity_id}{bright_info}")
                print()
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(list_lights())
