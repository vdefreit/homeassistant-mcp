"""
Home Assistant client for the AI Automation Assistant.

Provides async access to the HA REST API and direct YAML file operations
for automation management. Uses a persistent httpx client for connection
pooling and async file I/O throughout.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

import aiofiles
import httpx
import yaml

logger = logging.getLogger(__name__)

# Default when running inside HA Supervisor
_DEFAULT_AUTOMATIONS_PATH = "/config/automations.yaml"


class HomeAssistantClient:
    """Async client for the Home Assistant Supervisor API."""

    def __init__(
        self,
        url: str,
        token: str,
        automations_path: str = _DEFAULT_AUTOMATIONS_PATH,
    ) -> None:
        self.url = url.rstrip("/")
        self.automations_path = Path(automations_path)
        self._client = httpx.AsyncClient(
            base_url=f"{self.url}/api",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(30.0, connect=10.0),
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Core API helpers
    # ------------------------------------------------------------------

    async def _get(self, path: str) -> Any:
        resp = await self._client.get(path)
        resp.raise_for_status()
        return resp.json()

    async def _post(self, path: str, data: Optional[dict] = None) -> Any:
        resp = await self._client.post(path, json=data or {})
        resp.raise_for_status()
        return resp.json()

    async def _render_template(self, template: str) -> str:
        resp = await self._client.post("/template", json={"template": template})
        resp.raise_for_status()
        return resp.text

    # ------------------------------------------------------------------
    # Entity / state queries
    # ------------------------------------------------------------------

    async def get_states(self) -> list[dict]:
        """Return all entity states."""
        return await self._get("/states")

    async def get_state(self, entity_id: str) -> dict:
        """Return state + attributes for a single entity."""
        return await self._get(f"/states/{entity_id}")

    async def get_areas(self) -> list[dict]:
        """Return all areas with their names and entity IDs."""
        template = (
            "{% set ns = namespace(a=[]) %}"
            "{% for aid in areas() %}"
            "{% set ns.a = ns.a + [{'id': aid, 'name': area_name(aid), 'entities': area_entities(aid) | list}] %}"
            "{% endfor %}"
            "{{ ns.a | tojson }}"
        )
        raw = await self._render_template(template)
        return json.loads(raw)

    async def get_entity_summary(self) -> dict[str, int]:
        """Return a {domain: count} mapping of all entities."""
        states = await self.get_states()
        domains: dict[str, int] = {}
        for s in states:
            domain = s["entity_id"].split(".", 1)[0]
            domains[domain] = domains.get(domain, 0) + 1
        return dict(sorted(domains.items()))

    # ------------------------------------------------------------------
    # Service calls
    # ------------------------------------------------------------------

    async def call_service(
        self,
        domain: str,
        service: str,
        service_data: Optional[dict] = None,
    ) -> list[dict]:
        """Call a HA service (e.g. light/turn_on)."""
        return await self._post(
            f"/services/{domain}/{service}",
            data=service_data or {},
        )

    # ------------------------------------------------------------------
    # Automation management (direct YAML file access)
    # ------------------------------------------------------------------

    async def _read_automations(self) -> list[dict]:
        """Read the current automations list from YAML."""
        if not self.automations_path.exists():
            return []
        async with aiofiles.open(self.automations_path, "r", encoding="utf-8") as f:
            content = await f.read()
        if not content.strip():
            return []
        loaded = yaml.safe_load(content)
        if loaded is None:
            return []
        if not isinstance(loaded, list):
            return [loaded]
        return loaded

    async def _write_automations(self, automations: list[dict]) -> None:
        """Write the automations list back to YAML, creating a backup first."""
        backup = self.automations_path.with_suffix(".yaml.bak")
        if self.automations_path.exists():
            async with aiofiles.open(self.automations_path, "r", encoding="utf-8") as src:
                content = await src.read()
            async with aiofiles.open(backup, "w", encoding="utf-8") as dst:
                await dst.write(content)

        output = yaml.safe_dump(
            automations,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
        async with aiofiles.open(self.automations_path, "w", encoding="utf-8") as f:
            await f.write(output)

    async def reload_automations(self) -> None:
        """Tell HA to reload automations from disk."""
        await self._post("/services/automation/reload")

    async def list_automations(self) -> list[dict]:
        """Return all automations with id, alias, and description."""
        automations = await self._read_automations()
        return [
            {
                "id": a.get("id", ""),
                "alias": a.get("alias", ""),
                "description": a.get("description", ""),
            }
            for a in automations
        ]

    async def delete_automation(self, automation_id: str) -> bool:
        """Delete an automation by ID and reload. Returns True if found."""
        automations = await self._read_automations()
        filtered = [a for a in automations if a.get("id") != automation_id]
        if len(filtered) == len(automations):
            return False
        await self._write_automations(filtered)
        try:
            await self.reload_automations()
        except httpx.HTTPError:
            logger.warning("Automation deleted but reload failed.")
        return True

    async def create_automation(self, automation: dict) -> str:
        """Append an automation to YAML, reload, and return its generated ID."""
        automation_id = f"ai_{int(time.time())}"
        automation["id"] = automation_id

        automations = await self._read_automations()
        automations.append(automation)
        await self._write_automations(automations)

        try:
            await self.reload_automations()
        except httpx.HTTPError:
            logger.warning("Automation written but reload failed — HA may need a manual reload.")

        logger.info("Created automation %s (%s)", automation_id, automation.get("alias"))
        return automation_id
