# ⚡ Energy Reporter for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz)
[![GitHub Release](https://img.shields.io/github/v/release/Ambrosiussen/ha-energy-monthly-report)](https://github.com/Ambrosiussen/ha-energy-monthly-report/releases)
[![License: MIT](https://img.shields.io/github/license/Ambrosiussen/ha-energy-monthly-report)](LICENSE)

A Home Assistant custom integration that automatically generates professional monthly PDF energy reports — perfect for business expense tracking, landlord billing, or just keeping tabs on your energy usage.

---

## Features

- **Automatic monthly PDF reports** — generated on the 1st of every month at 06:00
- **Manual generation** — trigger a report any time via a service call
- **Current month support** — generate a partial report for the month in progress
- **Per-sensor daily breakdown** — tracks each energy meter with daily kWh consumption and cost
- **Configurable electricity tariff** — set your rate in €/kWh
- **Email delivery** — optionally send the PDF report as an attachment via an SMTP notify entity
- **Sensor entity** — exposes report metadata (total kWh, cost, month, download URL) for use in automations
- **Persistent notifications** — get a summary with a clickable download link in HA
- **Beautiful PDF layout** — styled with KPI cards, daily tables, and a combined summary for multiple meters

## Requirements

- Home Assistant **2023.6.0** or newer
- Energy sensors must have:
  - `state_class: total_increasing` or `total`
  - `device_class: energy`
  - `unit_of_measurement: kWh`
- The sensors must be recording **long-term statistics** (this is automatic for sensors with the above attributes)

## Installation

### HACS (Recommended)

1. Open **HACS** → **Integrations**
2. Click the three dots menu (top right) → **Custom repositories**
3. Add `https://github.com/Ambrosiussen/ha-energy-monthly-report` with category **Integration**
4. Search for **Energy Reporter** and click **Download**
5. Restart Home Assistant

### Manual

1. Copy the `custom_components/energy_reporter` folder into your `config/custom_components/` directory
2. Restart Home Assistant

## Setup

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for **Energy Reporter**
3. Configure the following:

| Option | Description |
|---|---|
| **Report name** | Label shown in the PDF header (e.g. "Office Energy") |
| **Energy sensors** | One or more energy sensors to include in the report |
| **Electricity rate** | Your tariff in €/kWh (default: 0.301648) |
| **Notify entity** *(optional)* | Notify entity to send the report to (e.g. `notify.smtp_you_example_com`) |
| **Email** *(optional)* | Recipient address; only needed with a legacy notify action (e.g. `notify.smtp`) |

All settings can be changed later via **Configure** on the integration card.

With an SMTP notify entity (one per recipient, under **Settings** → **Devices & Services** → **SMTP**) the PDF is attached via `smtp.send_message`. Any other notify entity gets the summary text only. Legacy SMTP notify actions such as `notify.smtp` still work but stop in Home Assistant 2027.3.

## Usage

### Automatic Reports

Reports are generated automatically at **06:00 on the 1st of each month**, covering the full previous month.

### Manual Reports

Trigger a report via **Developer Tools** → **Actions**:

```yaml
# Previous month
action: energy_reporter.generate_report
data: {}

# Current (partial) month
action: energy_reporter.generate_report_current_month
data: {}
```

### Accessing Reports

Generated PDFs are saved to `energy_reports/` in your media folder (`/media/energy_reports/` on Home Assistant OS). You can open them under **Media** → **My media**, or download one (logged in) at:

```
https://your-ha-instance/api/energy_reporter/report/energy_report_YYYY-MM.pdf
```

A direct download link is also included in the persistent notification after each report.

Before 1.3.0, reports were saved to `/config/www/reports/`, which Home Assistant serves to anyone under `/local/`. The download link still finds those old files; delete them once you don't need them.

### Sensor Entity

The integration creates a sensor entity named after the report (e.g. `sensor.office_energy_last_report`). Its state is the month of the last report, kept across restarts, with the following attributes:

| Attribute | Description |
|---|---|
| `last_report_month` | Report period (e.g. `2026-04`) |
| `last_total_kwh` | Total consumption in kWh |
| `last_total_cost_eur` | Total cost in EUR |
| `last_report_path` | Local file path to the PDF |
| `last_report_url` | Authenticated download URL |
| `generated_at` | Timestamp of last generation |

Use these in automations, dashboards, or template sensors.

## Troubleshooting

**Report shows 0 kWh:**
- Verify your sensor has `state_class: total_increasing` (check in Developer Tools → States)
- Check that the sensor appears in **Developer Tools → Statistics**
- The sensor must have been recording for at least a few hours to have statistics data

**No email received:**
- Ensure **Notify entity** is set in the integration options (plus **Email** for a legacy notify action)
- Test the entity independently first with `smtp.send_message`
- Check the log for `[energy_reporter] Failed to email report`

## License

[MIT](LICENSE)
