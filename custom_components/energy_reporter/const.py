"""Constants for the Energy Reporter integration."""

DOMAIN = "energy_reporter"

# Config entry keys
CONF_SENSORS       = "sensors"         # list of entity_ids
CONF_RATE          = "rate_eur_kwh"    # float, €/kWh
CONF_REPORT_NAME   = "report_name"     # friendly name shown in PDF header
CONF_EMAIL         = "email"           # recipient email address (optional)
CONF_NOTIFY_SERVICE = "notify_service" # notify entity, e.g. "notify.smtp_you_example_com"
                                       # (a legacy action like "notify.smtp" still works)

# Defaults
DEFAULT_RATE       = 0.301648

# Reports live in HA's media folder: smtp.send_message can only attach
# media-source items, and /config/www is served without auth under /local/.
REPORT_SUBDIR      = "energy_reports"
LEGACY_OUTPUT_DIR  = "/config/www/reports"  # before 1.3.0; still served for old links

# Services
SERVICE_GENERATE   = "generate_report"
SERVICE_GENERATE_CURRENT = "generate_report_current_month"

# Attributes exposed on the sensor entity
ATTR_LAST_REPORT   = "last_report_path"
ATTR_LAST_REPORT_URL = "last_report_url"
ATTR_LAST_KWH      = "last_total_kwh"
ATTR_LAST_COST     = "last_total_cost_eur"
ATTR_LAST_MONTH    = "last_report_month"
