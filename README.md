# Energy Reporter for Home Assistant

A custom Home Assistant integration that automatically generates monthly PDF energy reports for business expense tracking.

## Features

- **Automatic monthly reports** — generates a PDF on the 1st of every month at 06:00
- **Manual trigger** — call the `energy_reporter.generate_report` service any time
- **Per-sensor daily breakdown** — tracks each energy meter with daily kWh and cost
- **Configurable tariff** — set your electricity rate (€/kWh)
- **Sensor entity** — exposes report metadata (total kWh, cost, download URL)
- **Persistent notifications** — get notified with a summary and PDF download link

## Installation

### HACS (recommended)

1. Open **HACS** → **Integrations**
2. Click the three dots (top right) → **Custom repositories**
3. Add `https://github.com/Ambrosiussen/ha-energy-monthly-report` as **Integration**
4. Click **Download**
5. Restart Home Assistant

### Manual

Copy the `custom_components/energy_reporter` directory to your Home Assistant `config/custom_components/` directory and restart.

## Configuration

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for **Energy Reporter**
3. Configure:
   - **Report name** — label shown in the PDF header
   - **Energy sensors** — select one or more energy sensors (kWh)
   - **Electricity rate** — your tariff in €/kWh

## Usage

Reports are generated automatically on the 1st of each month, covering the previous month. You can also trigger a report manually via **Developer Tools** → **Services** → `energy_reporter.generate_report`.

Generated PDFs are saved to `/config/www/reports/` and accessible at `/local/reports/energy_report_YYYY-MM.pdf`.

## License

[MIT](LICENSE)
