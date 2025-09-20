"""OpenAI Usage Monitor integration (GUI-installable)."""
from __future__ import annotations
from datetime import timedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .api import OpenAIUsageClient
from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up OpenAI Usage Monitor from a config entry."""
    api_key = entry.data.get("api_key")
    update_interval = entry.data.get("update_interval", 3600)
    client = OpenAIUsageClient(api_key)

    async def async_update_data():
        # Fetch last 365 days (configurable later)
        data = await client.get_usage(days=365)
        # Ensure we always return a list under 'data' for compatibility with sensors
        if isinstance(data, dict) and "data" in data:
            return data.get("data", [])
        return data or []

    coordinator = DataUpdateCoordinator(
        hass,
        hass.logger,
        name="openai_usage_coordinator",
        update_method=async_update_data,
        update_interval=timedelta(seconds=update_interval),
    )

    # Perform first refresh
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Forward setup to sensor platform
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )

    return True
