"""Sensor platform for Energy Reporter."""

from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

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


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Energy Reporter sensor from a config entry."""
    async_add_entities([EnergyReporterSensor(entry)], update_before_add=False)


class EnergyReporterSensor(SensorEntity):
    """
    Sensor entity that surfaces metadata about the last generated report.
    State = month string (e.g. '2025-03'), attributes carry the details.
    """

    _attr_has_entity_name = True
    _attr_icon = "mdi:file-chart"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, entry: ConfigEntry) -> None:
        report_name = entry.data.get(CONF_REPORT_NAME, "Energy Reporter")
        self._entry = entry
        self._attr_name = f"{report_name} Last Report"
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_last_report"

        # State & attributes updated after each generation
        self._state: str | None = None
        self._extra: dict = {}

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
            "generated_at": datetime.now().isoformat(),
        }
        self.async_write_ha_state()
