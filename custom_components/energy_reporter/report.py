"""PDF report generation for Energy Reporter."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, List

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ── Palette ───────────────────────────────────────────────────────────────────
BRAND = colors.HexColor("#1B4F72")
ACCENT = colors.HexColor("#2E86C1")
LIGHT = colors.HexColor("#EBF5FB")
DIVIDE = colors.HexColor("#AED6F1")
DARK = colors.HexColor("#1A1A2E")
GREY = colors.HexColor("#717D7E")
STRIPE = colors.HexColor("#F4F6F7")
WHITE = colors.white


def generate_pdf(
    output_path: str,
    report_name: str,
    month_start: datetime,
    sensor_results: List[Dict],  # [{name, entity_id, total_kwh, daily: {date: kwh}}]
    rate: float,
) -> None:
    """Build and write the monthly energy PDF report."""

    month_label = month_start.strftime("%B %Y")
    grand_total_kwh = sum(r["total_kwh"] for r in sensor_results)
    grand_total_cost = grand_total_kwh * rate

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )

    W = A4[0] - 40 * mm
    styles = getSampleStyleSheet()

    def style(name, **kw):
        return ParagraphStyle(name, **kw)

    S = {
        "title": style(
            "t",
            fontSize=22,
            fontName="Helvetica-Bold",
            textColor=BRAND,
            alignment=TA_LEFT,
            spaceAfter=2,
        ),
        "subtitle": style(
            "st",
            fontSize=11,
            fontName="Helvetica",
            textColor=GREY,
            alignment=TA_LEFT,
            spaceAfter=10,
        ),
        "section": style(
            "se",
            fontSize=12,
            fontName="Helvetica-Bold",
            textColor=BRAND,
            spaceBefore=14,
            spaceAfter=6,
        ),
        "kpi_lbl": style(
            "kl", fontSize=9, fontName="Helvetica", textColor=GREY, alignment=TA_CENTER
        ),
        "kpi_val": style(
            "kv",
            fontSize=26,
            fontName="Helvetica-Bold",
            textColor=DARK,
            alignment=TA_CENTER,
            leading=30,
        ),
        "kpi_unit": style(
            "ku", fontSize=10, fontName="Helvetica", textColor=GREY, alignment=TA_CENTER
        ),
        "th": style(
            "th",
            fontSize=9,
            fontName="Helvetica-Bold",
            textColor=WHITE,
            alignment=TA_LEFT,
        ),
        "td": style(
            "td", fontSize=9, fontName="Helvetica", textColor=DARK, alignment=TA_LEFT
        ),
        "tdr": style(
            "tr", fontSize=9, fontName="Helvetica", textColor=DARK, alignment=TA_RIGHT
        ),
        "tot": style(
            "to",
            fontSize=9,
            fontName="Helvetica-Bold",
            textColor=WHITE,
            alignment=TA_LEFT,
        ),
        "totr": style(
            "tr2",
            fontSize=9,
            fontName="Helvetica-Bold",
            textColor=WHITE,
            alignment=TA_RIGHT,
        ),
        "info_k": style(
            "ik",
            fontSize=9,
            fontName="Helvetica-Bold",
            textColor=BRAND,
            alignment=TA_LEFT,
        ),
        "info_v": style(
            "iv", fontSize=9, fontName="Helvetica", textColor=DARK, alignment=TA_LEFT
        ),
        "footer": style(
            "fo", fontSize=8, fontName="Helvetica", textColor=GREY, alignment=TA_CENTER
        ),
    }

    story = []

    # ── Header ────────────────────────────────────────────────────────────────
    story.append(Paragraph(f"{report_name} — Energy Report", S["title"]))
    story.append(
        Paragraph(
            f"Period: {month_label}  ·  Generated {datetime.now().strftime('%d %b %Y, %H:%M')}",
            S["subtitle"],
        )
    )
    story.append(HRFlowable(width="100%", thickness=2, color=ACCENT, spaceAfter=16))

    # ── Top KPI cards ─────────────────────────────────────────────────────────
    def kpi(label, value, unit):
        return [
            Paragraph(label, S["kpi_lbl"]),
            Paragraph(value, S["kpi_val"]),
            Paragraph(unit, S["kpi_unit"]),
        ]

    n_sensors = len(sensor_results)
    days_all = set()
    for r in sensor_results:
        days_all.update(r["daily"].keys())
    avg_daily = grand_total_kwh / len(days_all) if days_all else 0

    kpi_data = [
        [
            kpi("Total Consumption", f"{grand_total_kwh:,.1f}", "kWh"),
            kpi("Total Cost", f"€ {grand_total_cost:,.2f}", f"@ €{rate}/kWh"),
            kpi("Daily Average", f"{avg_daily:,.2f}", "kWh/day"),
        ]
    ]
    kpi_table = Table(kpi_data, colWidths=[W / 3] * 3, rowHeights=[80])
    kpi_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
                ("GRID", (0, 0), (-1, -1), 1, WHITE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(kpi_table)
    story.append(Spacer(1, 18))

    # ── Config info ───────────────────────────────────────────────────────────
    story.append(Paragraph("Report Details", S["section"]))
    from dateutil.relativedelta import relativedelta

    end_day = month_start + relativedelta(months=1) - relativedelta(days=1)
    info_rows = [
        ["Report name", report_name],
        ["Tariff", f"€ {rate:.6f} / kWh  (fixed)"],
        [
            "Reporting period",
            f"{month_start.strftime('%d %B %Y')} — {end_day.strftime('%d %B %Y')}",
        ],
        ["Meters included", str(n_sensors)],
    ]
    info_table = Table(
        [[Paragraph(k, S["info_k"]), Paragraph(v, S["info_v"])] for k, v in info_rows],
        colWidths=[55 * mm, W - 55 * mm],
    )
    info_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), LIGHT),
                ("GRID", (0, 0), (-1, -1), 0.5, DIVIDE),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(info_table)
    story.append(Spacer(1, 18))

    # ── Per-sensor sections ───────────────────────────────────────────────────
    for result in sensor_results:
        sensor_kwh = result["total_kwh"]
        sensor_cost = sensor_kwh * rate
        daily = result["daily"]

        story.append(Paragraph(f"Meter: {result['name']}", S["section"]))
        story.append(
            Paragraph(
                f"Entity: {result['entity_id']}  ·  "
                f"Total: {sensor_kwh:,.3f} kWh  ·  Cost: € {sensor_cost:,.4f}",
                S["subtitle"],
            )
        )

        if not daily:
            story.append(Paragraph("No data available for this sensor.", S["td"]))
            story.append(Spacer(1, 12))
            continue

        header = [
            Paragraph("Date", S["th"]),
            Paragraph("Day", S["th"]),
            Paragraph("kWh", S["th"]),
            Paragraph("Cost (€)", S["th"]),
        ]
        rows = [header]
        for idx, (day_str, kwh) in enumerate(sorted(daily.items())):
            dt = datetime.strptime(day_str, "%Y-%m-%d")
            cost = kwh * rate
            rows.append(
                [
                    Paragraph(dt.strftime("%d %b %Y"), S["td"]),
                    Paragraph(dt.strftime("%A"), S["td"]),
                    Paragraph(f"{kwh:.3f}", S["tdr"]),
                    Paragraph(f"{cost:.4f}", S["tdr"]),
                ]
            )

        rows.append(
            [
                Paragraph("TOTAL", S["tot"]),
                Paragraph("", S["tot"]),
                Paragraph(f"{sensor_kwh:.3f}", S["totr"]),
                Paragraph(f"{sensor_cost:.4f}", S["totr"]),
            ]
        )

        col_w = [35 * mm, 40 * mm, W / 2 - 37.5 * mm, W / 2 - 37.5 * mm]
        t = Table(rows, colWidths=col_w, repeatRows=1)

        style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), BRAND),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.4, DIVIDE),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("BACKGROUND", (0, -1), (-1, -1), ACCENT),
            ("SPAN", (0, -1), (1, -1)),
        ]
        for idx in range(1, len(rows) - 1):
            if idx % 2 == 0:
                style_cmds.append(("BACKGROUND", (0, idx), (-1, idx), STRIPE))

        t.setStyle(TableStyle(style_cmds))
        story.append(t)
        story.append(Spacer(1, 16))

    # ── Grand total summary (only when >1 sensor) ─────────────────────────────
    if n_sensors > 1:
        story.append(HRFlowable(width="100%", thickness=1, color=DIVIDE, spaceAfter=8))
        story.append(Paragraph("Combined Summary", S["section"]))
        sum_rows = [
            [
                Paragraph("Meter", S["th"]),
                Paragraph("kWh", S["th"]),
                Paragraph("Cost (€)", S["th"]),
            ],
        ]
        for r in sensor_results:
            sum_rows.append(
                [
                    Paragraph(r["name"], S["td"]),
                    Paragraph(f"{r['total_kwh']:.3f}", S["tdr"]),
                    Paragraph(f"{r['total_kwh']*rate:.4f}", S["tdr"]),
                ]
            )
        sum_rows.append(
            [
                Paragraph("TOTAL", S["tot"]),
                Paragraph(f"{grand_total_kwh:.3f}", S["totr"]),
                Paragraph(f"{grand_total_cost:.4f}", S["totr"]),
            ]
        )
        sum_table = Table(sum_rows, colWidths=[W * 0.5, W * 0.25, W * 0.25])
        sum_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), BRAND),
                    ("BACKGROUND", (0, -1), (-1, -1), ACCENT),
                    ("GRID", (0, 0), (-1, -1), 0.4, DIVIDE),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(sum_table)

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=DIVIDE))
    story.append(Spacer(1, 6))
    story.append(
        Paragraph(
            f"Generated by Home Assistant · Energy Reporter integration · "
            f"{datetime.now().strftime('%d %b %Y %H:%M')}",
            S["footer"],
        )
    )

    doc.build(story)
