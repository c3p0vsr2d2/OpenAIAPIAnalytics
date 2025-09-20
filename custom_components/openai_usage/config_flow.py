import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN
from .api import OpenAIUsageClient

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required("api_key"): str,
    vol.Optional("update_interval", default=3600): int,
})

class OpenAIUsageConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            api_key = user_input["api_key"]
            update_interval = user_input.get("update_interval", 3600)
            # Validate API key quickly by requesting 1 day of usage
            try:
                client = OpenAIUsageClient(api_key)
                data = await client.get_usage(days=1)
                # accept if returned structure looks valid
                if not data:
                    errors["base"] = "invalid_api_key"
                else:
                    return self.async_create_entry(
                        title="OpenAI Usage Monitor",
                        data={"api_key": api_key, "update_interval": update_interval},
                    )
            except Exception:
                errors["base"] = "invalid_api_key"

        return self.async_show_form(step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors)
