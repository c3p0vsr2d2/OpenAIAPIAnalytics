import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required("api_key"): str,
    vol.Optional("update_interval", default=3600): int,
})

class OpenAIUsageConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for OpenAI Usage Monitor."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            api_key = user_input["api_key"]

            if not api_key.strip():
                errors["base"] = "invalid_api_key"
            else:
                # Save and exit flow
                return self.async_create_entry(
                    title="OpenAI Usage Monitor",
                    data={
                        "api_key": api_key.strip(),
                        "update_interval": user_input.get("update_interval", 3600),
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for OpenAI Usage Monitor."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={"update_interval": user_input["update_interval"]},
            )

        options_schema = vol.Schema({
            vol.Required(
                "update_interval",
                default=self.config_entry.options.get("update_interval", 3600)
            ): int
        })

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
            errors=errors,
        )
