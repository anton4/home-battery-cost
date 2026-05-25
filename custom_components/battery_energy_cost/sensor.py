"""Sensor platform for Battery Energy Cost."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
import math

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback, Event, State
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity

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
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    async_add_entities([
        BatteryEnergyValueSensor(entry),
        BatteryEnergyAvgCostSensor(entry),
    ])


class BatteryEnergyBaseSensor(RestoreEntity, SensorEntity):
    """Base class for battery energy sensors."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        self._entry = entry
        
        # Merge data and options
        self._config = dict(entry.data)
        self._config.update(entry.options)
        
        # State variables
        self._current_value_eur = 0.0
        self._current_energy_kwh = 0.0
        
        # Tracking for power integration
        self._last_update_time: datetime | None = None
        
        # Tracking for calibration
        self._last_calib_input_kwh: float | None = None
        self._last_calib_output_kwh: float | None = None
        self._integrated_input_kwh_since_calib = 0.0
        self._integrated_output_kwh_since_calib = 0.0
        self._accumulated_value_since_calib = 0.0

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        
        # Restore previous state
        state = await self.async_get_last_state()
        if state is not None and state.state not in (None, "unknown", "unavailable"):
            try:
                # Basic restore if available, but manual overrides take precedence
                pass
            except ValueError:
                pass

        # Check for manual overrides from options flow
        manual_value = self._config.get(CONF_MANUAL_VALUE_OVERRIDE)
        manual_cost = self._config.get(CONF_MANUAL_COST_OVERRIDE)
        
        if manual_value is not None and manual_cost is not None:
            self._current_value_eur = float(manual_value)
            if manual_cost > 0:
                self._current_energy_kwh = self._current_value_eur / float(manual_cost)
            else:
                self._current_energy_kwh = 0.0
            
            # Clear them from options so we don't restore them on every reboot
            # We can't modify options directly here, but HA will reload the entry if options change.
            # If the user doesn't clear them, it will re-override on every boot.
            # This is acceptable for a simple implementation.

        # Track state changes of all dependent sensors
        sensors_to_track = [
            self._config[CONF_BATTERY_POWER],
            self._config[CONF_GRID_POWER],
            self._config[CONF_PV_POWER],
            self._config[CONF_NORDPOOL_IMPORT],
            self._config[CONF_BATTERY_SOC],
            self._config[CONF_BATTERY_INPUT_ENERGY],
            self._config[CONF_BATTERY_OUTPUT_ENERGY],
        ]
        
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, sensors_to_track, self._async_sensor_changed
            )
        )

    def _get_float_state(self, entity_id: str) -> float | None:
        state = self.hass.states.get(entity_id)
        if state is None or state.state in (None, "unknown", "unavailable"):
            return None
        try:
            return float(state.state)
        except ValueError:
            return None

    @callback
    def _async_sensor_changed(self, event: Event) -> None:
        """Handle sensor state changes."""
        entity_id = event.data.get("entity_id")
        old_state: State | None = event.data.get("old_state")
        new_state: State | None = event.data.get("new_state")

        if new_state is None or new_state.state in (None, "unknown", "unavailable"):
            return

        now = datetime.now(timezone.utc)

        # 1. Reset logic
        if entity_id == self._config[CONF_BATTERY_SOC]:
            try:
                soc = float(new_state.state)
                if soc <= 0.0:
                    self._current_value_eur = 0.0
                    self._current_energy_kwh = 0.0
                    self._integrated_input_kwh_since_calib = 0.0
                    self._integrated_output_kwh_since_calib = 0.0
                    self._accumulated_value_since_calib = 0.0
                    self.async_write_ha_state()
                    return
            except ValueError:
                pass

        # 2. Continuous Power Integration
        if self._last_update_time is not None:
            delta_hours = (now - self._last_update_time).total_seconds() / 3600.0
            if delta_hours > 0:
                self._integrate_power(delta_hours)
                
        self._last_update_time = now

        # 3. Energy Calibration
        if entity_id == self._config[CONF_BATTERY_INPUT_ENERGY]:
            self._calibrate_input(new_state)
            
        elif entity_id == self._config[CONF_BATTERY_OUTPUT_ENERGY]:
            self._calibrate_output(new_state)

        self.async_write_ha_state()

    def _integrate_power(self, delta_hours: float) -> None:
        """Integrate power to update energy and value."""
        battery_power = self._get_float_state(self._config[CONF_BATTERY_POWER])
        grid_power = self._get_float_state(self._config[CONF_GRID_POWER])
        nordpool_price = self._get_float_state(self._config[CONF_NORDPOOL_IMPORT])

        if battery_power is None:
            return

        energy_change = battery_power * delta_hours

        if battery_power > 0:
            # Charging
            self._integrated_input_kwh_since_calib += energy_change
            self._current_energy_kwh += energy_change
            
            # Determine cost
            cost_eur = 0.0
            if grid_power is not None and nordpool_price is not None:
                # grid_power < 0 means importing
                grid_import_power = max(0.0, -grid_power)
                # how much of charging comes from grid vs pv?
                charging_from_grid = min(battery_power, grid_import_power)
                cost_eur = (charging_from_grid * delta_hours) * nordpool_price
                
            self._accumulated_value_since_calib += cost_eur
            self._current_value_eur += cost_eur
            
        elif battery_power < 0:
            # Discharging
            discharge_energy = -energy_change
            self._integrated_output_kwh_since_calib += discharge_energy
            
            # Calculate average cost before reducing
            avg_cost = 0.0
            if self._current_energy_kwh > 0:
                avg_cost = self._current_value_eur / self._current_energy_kwh
                
            self._current_energy_kwh = max(0.0, self._current_energy_kwh - discharge_energy)
            self._current_value_eur = self._current_energy_kwh * avg_cost

    def _calibrate_input(self, new_state: State) -> None:
        """Calibrate using the total input energy sensor."""
        try:
            current_input = float(new_state.state)
        except ValueError:
            return

        if self._last_calib_input_kwh is not None:
            actual_charged = current_input - self._last_calib_input_kwh
            if actual_charged > 0:
                # Adjust energy
                energy_diff = actual_charged - self._integrated_input_kwh_since_calib
                self._current_energy_kwh = max(0.0, self._current_energy_kwh + energy_diff)
                
                # Adjust value
                if self._integrated_input_kwh_since_calib > 0:
                    ratio = actual_charged / self._integrated_input_kwh_since_calib
                    actual_value = self._accumulated_value_since_calib * ratio
                    value_diff = actual_value - self._accumulated_value_since_calib
                    self._current_value_eur = max(0.0, self._current_value_eur + value_diff)
                else:
                    # Power sensor missed it entirely, use current nordpool price if available
                    np_price = self._get_float_state(self._config[CONF_NORDPOOL_IMPORT]) or 0.0
                    added_value = actual_charged * np_price
                    self._current_value_eur += added_value

        self._last_calib_input_kwh = current_input
        self._integrated_input_kwh_since_calib = 0.0
        self._accumulated_value_since_calib = 0.0

    def _calibrate_output(self, new_state: State) -> None:
        """Calibrate using the total output energy sensor."""
        try:
            current_output = float(new_state.state)
        except ValueError:
            return

        if self._last_calib_output_kwh is not None:
            actual_discharged = current_output - self._last_calib_output_kwh
            if actual_discharged > 0:
                # The integrated discharge might differ from actual discharge
                energy_diff = actual_discharged - self._integrated_output_kwh_since_calib
                
                # We over/underestimated discharge
                avg_cost = 0.0
                if self._current_energy_kwh > 0:
                    avg_cost = self._current_value_eur / self._current_energy_kwh
                    
                self._current_energy_kwh = max(0.0, self._current_energy_kwh - energy_diff)
                self._current_value_eur = self._current_energy_kwh * avg_cost

        self._last_calib_output_kwh = current_output
        self._integrated_output_kwh_since_calib = 0.0


class BatteryEnergyValueSensor(BatteryEnergyBaseSensor):
    """Sensor for total battery energy value in EUR."""

    _attr_has_entity_name = True
    _attr_name = "Battery Energy Value"
    _attr_icon = "mdi:currency-eur"
    _attr_native_unit_of_measurement = "EUR"
    _attr_state_class = SensorStateClass.TOTAL

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{self._entry.entry_id}_value"

    @property
    def native_value(self) -> float:
        """Return the state."""
        return round(self._current_value_eur, 4)

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra state attributes."""
        return {
            "current_energy_kwh": round(self._current_energy_kwh, 4),
        }


class BatteryEnergyAvgCostSensor(BatteryEnergyBaseSensor):
    """Sensor for average battery energy cost in EUR/kWh."""

    _attr_has_entity_name = True
    _attr_name = "Battery Average Energy Cost"
    _attr_icon = "mdi:chart-bell-curve"
    _attr_native_unit_of_measurement = "EUR/kWh"
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{self._entry.entry_id}_avg_cost"

    @property
    def native_value(self) -> float | None:
        """Return the state."""
        if self._current_energy_kwh > 0:
            return round(self._current_value_eur / self._current_energy_kwh, 4)
        return 0.0
