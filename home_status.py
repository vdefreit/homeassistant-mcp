#!/usr/bin/env python3
"""Get status update of what's online/active in the home."""

import asyncio
import os
from dotenv import load_dotenv
import httpx
from datetime import datetime

load_dotenv()

HA_URL = os.getenv("HA_URL", "http://localhost:8123").rstrip("/")
HA_TOKEN = os.getenv("HA_TOKEN")

async def get_home_status():
    """Get current status of home."""
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{HA_URL}/api/states", headers=headers)
        states = response.json()
        
        print(f"🏠 HOME STATUS - {datetime.now().strftime('%I:%M %p, %B %d, %Y')}\n")
        print("=" * 60)
        
        # People
        people = [s for s in states if s['entity_id'].startswith('person.')]
        print("\n👥 PEOPLE:")
        for person in people:
            name = person.get('attributes', {}).get('friendly_name', person['entity_id'])
            state = person['state']
            print(f"  • {name}: {state.upper()}")
        
        # Lights
        lights = [s for s in states if s['entity_id'].startswith('light.') and s['state'] == 'on']
        print(f"\n💡 LIGHTS ON ({len(lights)}):")
        if lights:
            for light in lights[:10]:  # Show first 10
                name = light.get('attributes', {}).get('friendly_name', light['entity_id'])
                brightness = light.get('attributes', {}).get('brightness')
                if brightness:
                    print(f"  • {name} (brightness: {int(brightness/255*100)}%)")
                else:
                    print(f"  • {name}")
            if len(lights) > 10:
                print(f"  ... and {len(lights)-10} more")
        else:
            print("  All lights are off")
        
        # Switches
        switches = [s for s in states if s['entity_id'].startswith('switch.') and s['state'] == 'on' and 'automation' not in s['entity_id'].lower()]
        print(f"\n🔌 SWITCHES ON ({len(switches)}):")
        if switches:
            for switch in switches[:10]:
                name = switch.get('attributes', {}).get('friendly_name', switch['entity_id'])
                print(f"  • {name}")
            if len(switches) > 10:
                print(f"  ... and {len(switches)-10} more")
        
        # Media Players
        media_players = [s for s in states if s['entity_id'].startswith('media_player.') and s['state'] in ['playing', 'paused', 'idle']]
        print(f"\n🔊 MEDIA PLAYERS:")
        if media_players:
            for player in media_players:
                name = player.get('attributes', {}).get('friendly_name', player['entity_id'])
                state = player['state']
                media = player.get('attributes', {}).get('media_title', '')
                if media:
                    print(f"  • {name}: {state.upper()} - {media}")
                else:
                    print(f"  • {name}: {state.upper()}")
        else:
            print("  No active media players")
        
        # Climate
        climate = [s for s in states if s['entity_id'].startswith('climate.')]
        print(f"\n🌡️  CLIMATE:")
        for device in climate:
            name = device.get('attributes', {}).get('friendly_name', device['entity_id'])
            temp = device.get('attributes', {}).get('current_temperature')
            target = device.get('attributes', {}).get('temperature')
            mode = device.get('attributes', {}).get('hvac_action', device['state'])
            if temp and target:
                print(f"  • {name}: {temp}°C → {target}°C ({mode})")
            else:
                print(f"  • {name}: {mode}")
        
        # Doors/Locks
        doors = [s for s in states if 'door' in s['entity_id'] and (s['entity_id'].startswith('lock.') or s['entity_id'].startswith('binary_sensor.'))]
        locks = [s for s in states if s['entity_id'].startswith('lock.')]
        if locks or doors:
            print(f"\n🚪 DOORS & LOCKS:")
            for lock in locks:
                name = lock.get('attributes', {}).get('friendly_name', lock['entity_id'])
                state = lock['state']
                print(f"  • {name}: {state.upper()}")
        
        # Automations
        automations = [s for s in states if s['entity_id'].startswith('automation.') and s['state'] == 'on']
        print(f"\n🤖 AUTOMATIONS ACTIVE: {len(automations)}")
        for auto in automations[:5]:
            name = auto.get('attributes', {}).get('friendly_name', auto['entity_id'])
            print(f"  • {name}")
        if len(automations) > 5:
            print(f"  ... and {len(automations)-5} more")
        
        print("\n" + "=" * 60)

asyncio.run(get_home_status())
