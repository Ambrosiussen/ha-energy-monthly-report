"""Data coordinator for Energy Reporter."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from dateutil.relativedelta import relativedelta
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import statistics_during_period
from homeassistant.core import HomeAssistant

from .const import CONF_RATE, CONF_REPORT_NAME, CONF_SENSORS, DOMAIN, OUTPUT_DIR

_LOGGER = logging.getLogger(__name__)


def _previous_month_bounds() -> tuple[datetime, datetime]:
    """Return UTC-aware start/end datetimes for the previous calendar month."""
    now = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    start = now.replace(day=1) - relativedelta(months=1)
    end = now.replace(day=1)
    return start, end


def _current_month_bounds() -> tuple[datetime, datetime]:
    """Return UTC-aware start/end datetimes for the current (partial) month."""
    now = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    start = now.replace(day=1)
    end = now + relativedelta(days=1)
    return start, end


def _consume_stats(stats: list) -> dict[str, float]:
    """
    Convert a list of hourly HA statistics entries into {date_str: kwh} daily totals.
    HA 'sum' is a running cumulative total; we take hourly deltas.
    """
    daily: dict[str, float] = {}
    prev_sum = None

    for entry in stats:
        s = entry.get("sum")
        if s is None:
            continue
        if prev_sum is not None:
            delta = max(0.0, s - prev_sum)  # guard against meter resets
            ts = entry.get("start")
            try:
                if isinstance(ts, (int, float)):
                    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                else:
                    dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                day_key = dt.strftime("%Y-%m-%d")
                daily[day_key] = daily.get(day_key, 0.0) + delta
            except (ValueError, TypeError):
                pass
        prev_sum = s

    return daily


async def generate_report(
    hass: HomeAssistant, config_entry, *, current_month: bool = False
) -> dict:
    """
    Fetch statistics for all configured sensors for the previous month
    (or current month if current_month=True) and generate the PDF.
    """
    data = {**config_entry.data, **config_entry.options}
    sensor_ids = data[CONF_SENSORS]
    rate = float(data[CONF_RATE])
    report_name = data[CONF_REPORT_NAME]

    start, end = _current_month_bounds() if current_month else _previous_month_bounds()
    month_label = start.strftime("%Y-%m")

    _LOGGER.info(
        "[energy_reporter] Generating report for %s — sensors: %s",
        month_label,
        sensor_ids,
    )

    # Fetch statistics via the recorder — must run in recorder executor
    def _fetch_all():
        results = []
        for entity_id in sensor_ids:
            raw = statistics_during_period(
                hass,
                start,
                end,
                {entity_id},
                period="hour",
                units={"energy": "kWh"},
                types={"sum"},
            )
            entries = raw.get(entity_id, [])
            if not entries:
                _LOGGER.warning(
                    "[energy_reporter] %s — no statistics entries returned. "
                    "Verify the entity has state_class 'total_increasing' or "
                    "'total' and is recording long-term statistics.",
                    entity_id,
                )
            daily = _consume_stats(entries)
            total = sum(daily.values())

            # Friendly name from state registry
            state = hass.states.get(entity_id)
            name = (
                state.attributes.get("friendly_name", entity_id) if state else entity_id
            )

            results.append(
                {
                    "entity_id": entity_id,
                    "name": name,
                    "total_kwh": total,
                    "daily": daily,
                }
            )
        return results

    sensor_results = await get_instance(hass).async_add_executor_job(_fetch_all)

    # Build PDF — import reportlab lazily inside executor to avoid blocking I/O
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filename = f"energy_report_{month_label}.pdf"
    output_path = os.path.join(OUTPUT_DIR, filename)
    report_url = f"/api/energy_reporter/report/{filename}"

    def _build_pdf():
        from .report import generate_pdf

        generate_pdf(output_path, report_name, start, sensor_results, rate)

    await hass.async_add_executor_job(_build_pdf)

    grand_kwh = sum(r["total_kwh"] for r in sensor_results)
    grand_cost = grand_kwh * rate

    _LOGGER.info(
        "[energy_reporter] Report saved → %s  (%.2f kWh, € %.2f)",
        output_path,
        grand_kwh,
        grand_cost,
    )

    return {
        "path": output_path,
        "url": report_url,
        "month": month_label,
        "total_kwh": grand_kwh,
        "total_cost": grand_cost,
    }
