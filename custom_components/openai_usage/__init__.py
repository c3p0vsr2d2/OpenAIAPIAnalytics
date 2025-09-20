"""OpenAI Usage Monitor integration."""
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .api import OpenAIUsageClient
from .const import DOMAIN
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
import asyncio
from datetime import date

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up OpenAI Usage Monitor from a config entry."""
    api_key = entry.data.get("api_key")
    client = OpenAIUsageClient(api_key)

    # Coordinator fetches last 365 days
    async def async_update_data():
        data = await client.get_usage(days=365)
        return data.get("data", [])

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER := hass.logger,
        name="openai_usage",
        update_method=async_update_data,
        update_interval=entry.options.get("update_interval", 3600),  # default 1h
    )

    await coordinator.async_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Load sensors
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )

    return True
