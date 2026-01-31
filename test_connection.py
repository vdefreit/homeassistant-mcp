#!/usr/bin/env python3
"""
Test script to verify Home Assistant connection
"""

import asyncio
import os
from dotenv import load_dotenv
import httpx

load_dotenv()

HA_URL = os.getenv("HA_URL", "").rstrip("/")
HA_TOKEN = os.getenv("HA_TOKEN", "")

async def test_connection():
    """Test the Home Assistant connection."""
    print(f"Testing connection to: {HA_URL}")
    
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }
    
    async with httpx.AsyncClient() as client:
        try:
            # Test API connection
            response = await client.get(f"{HA_URL}/api/", headers=headers, timeout=10.0)
            response.raise_for_status()
            print("✓ Connection successful!")
            print(f"✓ API Response: {response.json()}")
            
            # Get entity count
            states_response = await client.get(f"{HA_URL}/api/states", headers=headers, timeout=10.0)
            states_response.raise_for_status()
            states = states_response.json()
            print(f"✓ Found {len(states)} entities")
            
            # Show some sample entities
            print("\nSample entities:")
            for state in states[:5]:
                entity_id = state.get("entity_id")
                entity_state = state.get("state")
                friendly_name = state.get("attributes", {}).get("friendly_name", "N/A")
                print(f"  - {entity_id}: {entity_state} ({friendly_name})")
            
        except httpx.HTTPError as e:
            print(f"✗ Connection failed: {e}")
        except Exception as e:
            print(f"✗ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
