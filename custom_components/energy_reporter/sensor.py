"""Sensor platform for Energy Reporter."""

from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    ATTR_LAST_COST,
    ATTR_LAST_KWH,
    ATTR_LAST_MONTH,
    ATTR_LAST_REPORT,
    ATTR_LAST_REPORT_URL,
    CONF_REPORT_NAME,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

ATTR_GENERATED_AT = "generated_at"
RESTORED_ATTRS = (
    ATTR_LAST_MONTH,
    ATTR_LAST_KWH,
    ATTR_LAST_COST,
    ATTR_LAST_REPORT,
    ATTR_LAST_REPORT_URL,
    ATTR_GENERATED_AT,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Energy Reporter sensor from a config entry."""
    sensor = EnergyReporterSensor(entry)
    # _run_report in __init__.py pushes each new report into this sensor
    hass.data[DOMAIN][entry.entry_id]["sensor"] = sensor
    async_add_entities([sensor], update_before_add=False)


class EnergyReporterSensor(SensorEntity, RestoreEntity):
    """
    Sensor entity that surfaces metadata about the last generated report.
    State = month string (e.g. '2025-03'), attributes carry the details.
    No state_class: the state is text, not a measurement.
    """

    _attr_has_entity_name = True
    _attr_icon = "mdi:file-chart"

    def __init__(self, entry: ConfigEntry) -> None:
        report_name = entry.data.get(CONF_REPORT_NAME, "Energy Reporter")
        self._entry = entry
        self._attr_name = f"{report_name} Last Report"
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_last_report"

        # State & attributes updated after each generation
        self._state: str | None = None
        self._extra: dict = {}

    async def async_added_to_hass(self) -> None:
        """Restore the last report's details, which would otherwise reset on restart."""
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is None or last.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return
        self._state = last.state
        self._extra = {
            key: value for key, value in last.attributes.items() if key in RESTORED_ATTRS
        }

    @property
    def native_value(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return self._extra

    def update_from_result(self, result: dict) -> None:
        """Called by __init__.py after a successful report generation."""
        self._state = result["month"]
        self._extra = {
            ATTR_LAST_MONTH: result["month"],
            ATTR_LAST_KWH: round(result["total_kwh"], 3),
            ATTR_LAST_COST: round(result["total_cost"], 4),
            ATTR_LAST_REPORT: result["path"],
            ATTR_LAST_REPORT_URL: result["url"],
            ATTR_GENERATED_AT: datetime.now().isoformat(),
        }
        self.async_write_ha_state()
