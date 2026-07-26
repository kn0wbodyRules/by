"""PDF export for the Download screen — reportlab's Platypus Table handles
multi-page tables with repeated headers automatically, which matters since a
multi-room BOQ table can run long.
"""

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.schemas.boq import BOQResponse

PLACEHOLDER_DISCLAIMER = (
    "NOTE: Rates used in this estimate are PLACEHOLDER values, not verified Tamil Nadu "
    "PWD Schedule of Rates figures. Replace app/seed_data/rate_table_seed.json with real "
    "rates before using this for actual procurement or budgeting."
)


def generate_boq_pdf(boq: BOQResponse) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title=f"BOQ - {boq.project_name}")
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(f"Bill of Quantities — {boq.project_name}", styles["Title"]))
    elements.append(
        Paragraph(f"Location: {boq.location} | Generated: {boq.generated_at.isoformat()}", styles["Normal"])
    )
    elements.append(Spacer(1, 0.15 * inch))
    elements.append(Paragraph(PLACEHOLDER_DISCLAIMER, styles["Italic"]))
    elements.append(Spacer(1, 0.25 * inch))

    header = ["Room", "Material", "Qty", "Unit", "Rate/Unit", "Total Cost"]
    data = [header]
    for room in boq.rooms:
        for material in room.materials:
            data.append(
                [
                    room.room_name,
                    material.material_name,
                    f"{material.quantity:.2f}",
                    material.unit,
                    f"{material.rate_per_unit:,.2f}",
                    f"{material.total_cost:,.2f}",
                ]
            )

    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#36355b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6e3c5")]),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
            ]
        )
    )
    elements.append(table)

    elements.append(Spacer(1, 0.25 * inch))
    elements.append(Paragraph(f"Total Cost: {boq.currency} {boq.total_cost:,.2f}", styles["Heading2"]))

    doc.build(elements)
    return buffer.getvalue()
