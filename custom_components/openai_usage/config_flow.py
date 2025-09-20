import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("api_key"): str,
        vol.Optional("update_interval", default=3600): int,
    }
)

class OpenAIUsageConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for OpenAI Usage Monitor."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            api_key = user_input["api_key"]
            update_interval = user_input.get("update_interval", 3600)

            # Optional: validate API key by calling OpenAI usage endpoint
            valid = await self._test_api_key(api_key)
            if not valid:
                errors["api_key"] = "invalid_api_key"
            else:
                return self.async_create_entry(
                    title="OpenAI Usage Monitor",
                    data={
                        "api_key": api_key,
                        "update_interval": update_interval,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def _test_api_key(self, api_key):
        """Optional: test if the API key works by calling usage endpoint."""
        from .api import OpenAIUsageClient

        try:
            client = OpenAIUsageClient(api_key)
            data = await client.get_usage(days=1)
            return "data" in data
        except Exception:
            return False
