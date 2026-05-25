"""Config flow for Battery Energy Cost integration."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_BATTERY_INPUT_ENERGY,
    CONF_BATTERY_OUTPUT_ENERGY,
    CONF_BATTERY_POWER,
    CONF_GRID_POWER,
    CONF_PV_POWER,
    CONF_NORDPOOL_IMPORT,
    CONF_BATTERY_SOC,
    CONF_MANUAL_VALUE_OVERRIDE,
    CONF_MANUAL_COST_OVERRIDE,
    DEFAULT_BATTERY_INPUT_ENERGY,
    DEFAULT_BATTERY_OUTPUT_ENERGY,
    DEFAULT_BATTERY_POWER,
    DEFAULT_GRID_POWER,
    DEFAULT_PV_POWER,
    DEFAULT_NORDPOOL_IMPORT,
    DEFAULT_BATTERY_SOC,
)

def get_schema(defaults: dict) -> vol.Schema:
    """Return the data schema."""
    return vol.Schema({
        vol.Required(CONF_BATTERY_INPUT_ENERGY, default=defaults.get(CONF_BATTERY_INPUT_ENERGY, DEFAULT_BATTERY_INPUT_ENERGY)): selector.EntitySelector(
            selector.EntitySelectorConfig(device_class=SensorDeviceClass.ENERGY)
        ),
        vol.Required(CONF_BATTERY_OUTPUT_ENERGY, default=defaults.get(CONF_BATTERY_OUTPUT_ENERGY, DEFAULT_BATTERY_OUTPUT_ENERGY)): selector.EntitySelector(
            selector.EntitySelectorConfig(device_class=SensorDeviceClass.ENERGY)
        ),
        vol.Required(CONF_BATTERY_POWER, default=defaults.get(CONF_BATTERY_POWER, DEFAULT_BATTERY_POWER)): selector.EntitySelector(
            selector.EntitySelectorConfig(device_class=SensorDeviceClass.POWER)
        ),
        vol.Required(CONF_GRID_POWER, default=defaults.get(CONF_GRID_POWER, DEFAULT_GRID_POWER)): selector.EntitySelector(
            selector.EntitySelectorConfig(device_class=SensorDeviceClass.POWER)
        ),
        vol.Required(CONF_PV_POWER, default=defaults.get(CONF_PV_POWER, DEFAULT_PV_POWER)): selector.EntitySelector(
            selector.EntitySelectorConfig(device_class=SensorDeviceClass.POWER)
        ),
        vol.Required(CONF_NORDPOOL_IMPORT, default=defaults.get(CONF_NORDPOOL_IMPORT, DEFAULT_NORDPOOL_IMPORT)): selector.EntitySelector(
            selector.EntitySelectorConfig()
        ),
        vol.Required(CONF_BATTERY_SOC, default=defaults.get(CONF_BATTERY_SOC, DEFAULT_BATTERY_SOC)): selector.EntitySelector(
            selector.EntitySelectorConfig(device_class=SensorDeviceClass.BATTERY)
        ),
        vol.Optional(CONF_MANUAL_VALUE_OVERRIDE): vol.Coerce(float),
        vol.Optional(CONF_MANUAL_COST_OVERRIDE): vol.Coerce(float),
    })

class BatteryEnergyCostConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Battery Energy Cost."""

    VERSION = 1

    @staticmethod
    @config_entries.callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> BatteryEnergyCostOptionsFlow:
        """Get the options flow for this handler."""
        return BatteryEnergyCostOptionsFlow(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            # We don't save the manual overrides in the core config data, 
            # we can just put them in options so it's consistent.
            return self.async_create_entry(title="Battery Energy Cost", data={}, options=user_input)

        return self.async_show_form(
            step_id="user", data_schema=get_schema({})
        )

class BatteryEnergyCostOptionsFlow(config_entries.OptionsFlow):
    """Handle options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=get_schema(self.config_entry.options),
        )
