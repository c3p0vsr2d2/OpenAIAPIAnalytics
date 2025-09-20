async def async_setup_entry(hass, entry):
    """Set up OpenAI Usage Monitor from config entry."""
    from .api import OpenAIUsageClient
    from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

    api_key = entry.data.get("api_key")
    client = OpenAIUsageClient(api_key)

    async def async_update_data():
        data = await client.get_usage(days=365)
        return data.get("data", [])

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER := hass.logger,
        name="openai_usage",
        update_method=async_update_data,
        update_interval=entry.data.get("update_interval", 3600),
    )

    await coordinator.async_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )

    return True
