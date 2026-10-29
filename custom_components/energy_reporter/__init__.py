"""Energy Reporter — Home Assistant custom integration."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.network import get_url
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_EMAIL,
    CONF_NOTIFY_SERVICE,
    DOMAIN,
    LEGACY_OUTPUT_DIR,
    SERVICE_GENERATE,
    SERVICE_GENERATE_CURRENT,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]


class ReportDownloadView(HomeAssistantView):
    """Serve generated PDF reports."""

    url = "/api/energy_reporter/report/{filename}"
    name = "api:energy_reporter:report"
    requires_auth = True

    def __init__(self, report_dirs: list[str]) -> None:
        self._report_dirs = report_dirs

    async def get(self, request: web.Request, filename: str) -> web.StreamResponse:
        # Prevent path traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            return web.Response(status=403)
        for report_dir in self._report_dirs:
            filepath = os.path.join(report_dir, filename)
            if os.path.isfile(filepath):
                return web.FileResponse(filepath)
        return web.Response(status=404, text="Report not found")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Energy Reporter from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"sensor": None}

    # Register the download view once
    if "view_registered" not in hass.data[DOMAIN]:
        from .coordinator import report_location

        hass.http.register_view(
            ReportDownloadView([report_location(hass)[1], LEGACY_OUTPUT_DIR])
        )
        hass.data[DOMAIN]["view_registered"] = True

    # Forward to sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # ── Monthly trigger: fires at 06:00 on the 1st of every month ─────────────
    async def _monthly_trigger(now: datetime) -> None:
        if now.day != 1:
            return
        _LOGGER.info(
            "[energy_reporter] Monthly trigger fired for entry %s", entry.entry_id
        )
        await _run_report(hass, entry)

    entry.async_on_unload(
        async_track_time_change(hass, _monthly_trigger, hour=6, minute=0, second=0)
    )

    # ── Service: energy_reporter.generate_report ───────────────────────────────
    async def _handle_service(call: ServiceCall) -> None:
        """Allow manual trigger via service call."""
        _LOGGER.info("[energy_reporter] Manual service call received")
        for eid, store in hass.data[DOMAIN].items():
            cfg = hass.config_entries.async_get_entry(eid)
            if cfg:
                await _run_report(hass, cfg)

    if not hass.services.has_service(DOMAIN, SERVICE_GENERATE):
        hass.services.async_register(DOMAIN, SERVICE_GENERATE, _handle_service)

    # ── Service: energy_reporter.generate_report_current_month ─────────────────
    async def _handle_service_current(call: ServiceCall) -> None:
        """Allow manual trigger for current month via service call."""
        _LOGGER.info("[energy_reporter] Manual service call received (current month)")
        for eid, store in hass.data[DOMAIN].items():
            cfg = hass.config_entries.async_get_entry(eid)
            if cfg:
                await _run_report(hass, cfg, current_month=True)

    if not hass.services.has_service(DOMAIN, SERVICE_GENERATE_CURRENT):
        hass.services.async_register(
            DOMAIN, SERVICE_GENERATE_CURRENT, _handle_service_current
        )

    # Reload options if changed
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _run_report(
    hass: HomeAssistant, entry: ConfigEntry, *, current_month: bool = False
) -> None:
    """Generate report and push result to the sensor entity."""
    from .coordinator import generate_report

    try:
        result = await generate_report(hass, entry, current_month=current_month)
    except Exception as exc:
        _LOGGER.error("[energy_reporter] Report generation failed: %s", exc)
        _send_notification(hass, f"Energy Reporter failed: {exc}", is_error=True)
        return

    # Update sensor state
    store = hass.data[DOMAIN].get(entry.entry_id, {})
    sensor = store.get("sensor")
    if sensor:
        sensor.update_from_result(result)

    # Persistent notification with download link (full URL so it opens in browser)
    try:
        base_url = get_url(hass)
    except Exception:
        base_url = ""
    full_url = f"{base_url}{result['url']}"
    _send_notification(
        hass,
        f"Report for **{result['month']}** is ready.\n\n"
        f"- Total: **{result['total_kwh']:.2f} kWh**\n"
        f"- Cost: **€ {result['total_cost']:.2f}**\n\n"
        f"[Download Report]({full_url})",
    )

    # Email the report if configured
    data = {**entry.data, **entry.options}
    email = data.get(CONF_EMAIL, "").strip()
    notify_service = data.get(CONF_NOTIFY_SERVICE, "").strip()
    if notify_service:
        await _send_email(hass, notify_service, email, result)


async def _send_email(
    hass: HomeAssistant, notify_service: str, email: str, result: dict
) -> None:
    """Send the report PDF via a notify entity, or a legacy notify action."""
    title = f"Energy Report — {result['month']}"
    message = (
        f"Energy report for {result['month']} is ready.\n\n"
        f"Total: {result['total_kwh']:.2f} kWh\n"
        f"Cost: € {result['total_cost']:.2f}"
    )
    entity = er.async_get(hass).async_get(notify_service)
    try:
        if entity is not None and entity.domain == "notify":
            if entity.platform == "smtp":
                # The entity is the recipient; the PDF goes as a media-source attachment
                await hass.services.async_call(
                    "smtp",
                    "send_message",
                    {
                        "title": title,
                        "message": message,
                        "attachments": [
                            {
                                "media_source": {
                                    "media_content_id": result["media_content_id"],
                                    "media_content_type": "application/pdf",
                                },
                                "filename": result["filename"],
                            }
                        ],
                    },
                    blocking=True,
                    target={"entity_id": notify_service},
                )
            else:
                # notify.send_message carries no attachments; send the summary only
                await hass.services.async_call(
                    "notify",
                    "send_message",
                    {"title": title, "message": message},
                    blocking=True,
                    target={"entity_id": notify_service},
                )
        else:
            # Legacy notify action such as "notify.smtp" (SMTP drops these in 2027.3)
            parts = notify_service.split(".", 1)
            if len(parts) != 2 or not email:
                _LOGGER.error(
                    "[energy_reporter] %s is not a notify entity, and a legacy "
                    "notify action needs an email address",
                    notify_service,
                )
                return
            domain, service = parts
            await hass.services.async_call(
                domain,
                service,
                {
                    "message": message,
                    "title": title,
                    "target": [email],
                    "data": {
                        "images": [result["path"]],
                    },
                },
                blocking=True,
            )
        _LOGGER.info("[energy_reporter] Report sent via %s", notify_service)
    except Exception as exc:
        _LOGGER.error("[energy_reporter] Failed to email report: %s", exc)


def _send_notification(
    hass: HomeAssistant, message: str, is_error: bool = False
) -> None:
    hass.async_create_task(
        hass.services.async_call(
            "persistent_notification",
            "create",
            {
                "title": "⚡ Energy Reporter" + (" — Error" if is_error else ""),
                "message": message,
                "notification_id": f"{DOMAIN}_report",
            },
        )
    )


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload entry when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the integration."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        # Remove service if no entries remain
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_GENERATE)
            hass.services.async_remove(DOMAIN, SERVICE_GENERATE_CURRENT)
    return unloaded
