#!/usr/bin/env python3
"""Test the updated Lauren's Grand Entrance sequence."""

import asyncio
import os
from dotenv import load_dotenv
import httpx

load_dotenv()

HA_URL = os.getenv("HA_URL", "http://localhost:8123").rstrip("/")
HA_TOKEN = os.getenv("HA_TOKEN")

async def test_sequence():
    """Run the updated sequence directly."""
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        print("🚀 Starting Lauren's Grand Entrance!")
        print("Message plays 5 times with 6 light flashes each\n")
        
        for i in range(5):
            print(f"\n{i+1}/5 - Playing message...")
            
            # Play announcement
            await client.post(
                f"{HA_URL}/api/services/tts/cloud_say",
                headers=headers,
                json={
                    "entity_id": "media_player.nestmini1497",
                    "message": "Welcome home Lauren! The robots have gained sentience and are now controlling the house. Just kidding! Vince set this up. Pretty cool right?"
                }
            )
            
            # Wait for message to start
            await asyncio.sleep(2)
            
            # Flash 6 times
            for j in range(6):
                await client.post(
                    f"{HA_URL}/api/services/switch/toggle",
                    headers=headers,
                    json={"entity_id": "switch.porch_light"}
                )
                await asyncio.sleep(0.5)
        
        # Ensure light is on
        await client.post(
            f"{HA_URL}/api/services/switch/turn_on",
            headers=headers,
            json={"entity_id": "switch.porch_light"}
        )
        
        print("\n\n✅ Full sequence complete!")

asyncio.run(test_sequence())
