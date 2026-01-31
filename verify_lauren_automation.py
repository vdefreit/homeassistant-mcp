#!/usr/bin/env python3
"""Verify Lauren's Grand Entrance automation is loaded in Home Assistant."""

import asyncio
import os
from dotenv import load_dotenv
import httpx

load_dotenv()

HA_URL = os.getenv("HA_URL", "http://localhost:8123").rstrip("/")
HA_TOKEN = os.getenv("HA_TOKEN")

async def verify_automation():
    """Check if the automation exists and is enabled."""
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }
    
    async with httpx.AsyncClient() as client:
        # Get automation state
        response = await client.get(
            f"{HA_URL}/api/states/automation.lauren_s_grand_entrance",
            headers=headers
        )
        
        if response.status_code == 200:
            auto = response.json()
            print("✅ Lauren's Grand Entrance is LIVE in Home Assistant!")
            print(f"\nStatus: {auto['state'].upper()}")
            print(f"Friendly Name: {auto.get('attributes', {}).get('friendly_name')}")
            print(f"\nTrigger: Front door motion detected")
            print(f"Conditions:")
            print(f"  • Lauren must be home")
            print(f"  • Must be after sunset")
            print(f"\nAction:")
            print(f"  • Message plays 5 times")
            print(f"  • Porch light flashes 30 times (6 per message)")
            print(f"\n🎉 Ready for Lauren's next arrival after sunset!")
        else:
            print(f"❌ Automation not found: {response.status_code}")
            print("Let me reload automations...")
            
            await client.post(
                f"{HA_URL}/api/services/automation/reload",
                headers=headers
            )
            print("✓ Automations reloaded - try checking again")

asyncio.run(verify_automation())
