"""Config flow for Energy Reporter."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    EntitySelector,
    NumberSelector,
    TextSelector,
)

from .const import (
    DOMAIN,
    CONF_EMAIL,
    CONF_NOTIFY_SERVICE,
    CONF_RATE,
    CONF_REPORT_NAME,
    CONF_SENSORS,
    DEFAULT_RATE,
)

ENTITY_SELECTOR = EntitySelector(
    {
        "multiple": True,
        "filter": {"domain": "sensor", "device_class": "energy"},
    }
)

RATE_SELECTOR = NumberSelector(
    {
        "min": 0.0,
        "max": 5.0,
        "step": "any",
        "mode": "box",
        "unit_of_measurement": "€/kWh",
    }
)


class EnergyReporterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial setup config flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            # Validate at least one sensor is selected
            if not user_input.get(CONF_SENSORS):
                errors[CONF_SENSORS] = "no_sensors"
            else:
                # Use report name as unique ID so duplicate setups are prevented
                unique_id = f"energy_reporter_{user_input[CONF_REPORT_NAME].lower().replace(' ', '_')}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=user_input[CONF_REPORT_NAME],
                    data=user_input,
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_REPORT_NAME, default="Home Energy"): TextSelector(),
                vol.Required(CONF_SENSORS): ENTITY_SELECTOR,
                vol.Required(CONF_RATE, default=DEFAULT_RATE): RATE_SELECTOR,
                vol.Optional(CONF_EMAIL, default=""): TextSelector(),
                vol.Optional(CONF_NOTIFY_SERVICE, default=""): TextSelector(),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return EnergyReporterOptionsFlow(config_entry)


class EnergyReporterOptionsFlow(config_entries.OptionsFlow):
    """Allow editing rate and sensors after setup."""

    def __init__(self, config_entry):
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        errors = {}

        if user_input is not None:
            if not user_input.get(CONF_SENSORS):
                errors[CONF_SENSORS] = "no_sensors"
            else:
                return self.async_create_entry(title="", data=user_input)

        current = self._config_entry.data

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_REPORT_NAME,
                    default=current.get(CONF_REPORT_NAME, "Home Energy"),
                ): TextSelector(),
                vol.Required(
                    CONF_SENSORS, default=current.get(CONF_SENSORS, [])
                ): ENTITY_SELECTOR,
                vol.Required(
                    CONF_RATE, default=current.get(CONF_RATE, DEFAULT_RATE)
                ): RATE_SELECTOR,
                vol.Optional(
                    CONF_EMAIL, default=current.get(CONF_EMAIL, "")
                ): TextSelector(),
                vol.Optional(
                    CONF_NOTIFY_SERVICE,
                    default=current.get(CONF_NOTIFY_SERVICE, ""),
                ): TextSelector(),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
        )
