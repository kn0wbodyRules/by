"""CSV export for the Download screen.

One flat row per room x material, matching the Excel export's "BOQ Detail" sheet
so the three formats stay comparable. Project metadata is carried as leading
comment lines rather than a second table, since CSV has no concept of sheets and
a spreadsheet import should still see a clean single header row.
"""

import csv
from enum import Enum
from io import StringIO

from app.schemas.boq import BOQResponse


def _text(value: object) -> str:
    """The BOQ schema is inconsistent about enums — room_type and
    correction_confidence are Enum members while unit is a plain str — so
    normalise rather than assuming either."""
    return value.value if isinstance(value, Enum) else str(value)

COLUMNS = [
    "room_name",
    "room_type",
    "area_sqft",
    "material_name",
    "theoretical_quantity",
    "correction_factor",
    "correction_confidence",
    "quantity",
    "unit",
    "rate_per_unit",
    "total_cost",
]


def generate_boq_csv(boq: BOQResponse) -> bytes:
    buffer = StringIO(newline="")

    # Excel reads a leading "sep=," hint to pick the delimiter, and treats the
    # remaining metadata lines as ordinary text above the table.
    buffer.write(f"# Project,{boq.project_name}\n")
    buffer.write(f"# Location,{boq.location}\n")
    buffer.write(f"# Generated At,{boq.generated_at.isoformat()}\n")
    buffer.write(f"# Currency,{boq.currency}\n")
    buffer.write("#\n")

    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(COLUMNS)

    for room in boq.rooms:
        for material in room.materials:
            writer.writerow(
                [
                    room.room_name,
                    _text(room.room_type),
                    f"{room.area_sqft:.2f}",
                    material.material_name,
                    f"{material.theoretical_quantity:.4f}",
                    f"{material.correction_factor:.4f}",
                    _text(material.correction_confidence),
                    f"{material.quantity:.4f}",
                    _text(material.unit),
                    f"{material.rate_per_unit:.2f}",
                    f"{material.total_cost:.2f}",
                ]
            )

    writer.writerow([])
    writer.writerow(["TOTAL", "", "", "", "", "", "", "", "", "", f"{boq.total_cost:.2f}"])

    # utf-8-sig so Excel on Windows renders the rupee sign in project names
    # correctly instead of mojibake.
    return buffer.getvalue().encode("utf-8-sig")
