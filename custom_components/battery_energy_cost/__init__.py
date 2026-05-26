"""The Battery Energy Cost integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_MANUAL_VALUE_OVERRIDE, CONF_MANUAL_COST_OVERRIDE

PLATFORMS: list[Platform] = [Platform.SENSOR]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Battery Energy Cost from a config entry."""
    
    # Extract overrides and remove them from options so they only apply once
    options = dict(entry.options)
    overrides = {}
    if CONF_MANUAL_VALUE_OVERRIDE in options:
        overrides[CONF_MANUAL_VALUE_OVERRIDE] = options.pop(CONF_MANUAL_VALUE_OVERRIDE)
        if CONF_MANUAL_COST_OVERRIDE in options:
            overrides[CONF_MANUAL_COST_OVERRIDE] = options.pop(CONF_MANUAL_COST_OVERRIDE)
            
        # Update entry quietly before we add the listener
        hass.config_entries.async_update_entry(entry, options=options)
        
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = overrides

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
        hass.data[DOMAIN].pop(entry.entry_id)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
