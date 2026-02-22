#!/usr/bin/env python3
"""Update Lauren's automation to 30 flashes and 5 message plays."""

import yaml
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
import httpx

load_dotenv()

HA_URL = os.getenv("HA_URL", "http://localhost:8123").rstrip("/")
HA_TOKEN = os.getenv("HA_TOKEN")
AUTOMATIONS_PATH = r"Z:\automations.yaml"

async def update_lauren_automation():
    """Update the automation with reduced flashing and repeated messages."""
    
    # Read existing automations
    with open(AUTOMATIONS_PATH, 'r', encoding='utf-8') as f:
        automations = yaml.safe_load(f) or []
    
    # Remove old Lauren automation
    automations = [auto for auto in automations if auto.get('alias') != "Lauren's Grand Entrance"]
    
    # Create updated automation
    import time
    automation = {
        'id': f"mcp_{int(time.time())}",
        'alias': "Lauren's Grand Entrance",
        'description': "Flash porch light 30 times with 5 message repeats",
        'trigger': [
            {
                'platform': 'state',
                'entity_id': 'event.front_door_motion',
                'attribute': 'event_type',
                'to': 'motion'
            }
        ],
        'condition': [
            {
                'condition': 'state',
                'entity_id': 'person.lauren_cahill',
                'state': 'home'
            },
            {
                'condition': 'sun',
                'after': 'sunset'
            }
        ],
        'action': [
            # Repeat 5 times: message + 6 light flashes
            {
                'repeat': {
                    'count': 5,
                    'sequence': [
                        # Play announcement
                        {
                            'service': 'tts.cloud_say',
                            'target': {'entity_id': 'media_player.nestmini1497'},
                            'data': {
                                'message': "Welcome home Lauren! The robots have gained sentience and are now controlling the house. Just kidding! Vince set this up. Pretty cool right?"
                            }
                        },
                        # Wait for message to start
                        {'delay': {'seconds': 2}},
                        # Flash 6 times (3 seconds)
                        {
                            'repeat': {
                                'count': 6,
                                'sequence': [
                                    {'service': 'switch.toggle', 'target': {'entity_id': 'switch.porch_light'}},
                                    {'delay': {'milliseconds': 500}}
                                ]
                            }
                        }
                    ]
                }
            },
            # Ensure porch light ends in ON state
            {'service': 'switch.turn_on', 'target': {'entity_id': 'switch.porch_light'}}
        ],
        'mode': 'single'
    }
    
    automations.append(automation)
    
    # Write back to file
    with open(AUTOMATIONS_PATH, 'w', encoding='utf-8') as f:
        yaml.safe_dump(automations, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    print(f"✓ Updated 'Lauren's Grand Entrance' automation!")
    print(f"ID: {automation['id']}")
    print(f"\nNew sequence:")
    print(f"  • Message plays 5 times")
    print(f"  • Porch light flashes 30 times total (6 flashes per message)")
    print(f"  • Total duration: ~25-30 seconds")
    
    # Reload automations
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }
    
    async with httpx.AsyncClient() as client:
        await client.post(f"{HA_URL}/api/services/automation/reload", headers=headers)
    
    print("\n✓ Automations reloaded")

asyncio.run(update_lauren_automation())
