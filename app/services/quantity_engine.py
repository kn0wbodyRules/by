"""Stage 4 — deterministic quantity engine. Plain geometric math, NOT ML.

Every function here is pure (no DB/HTTP imports) so it's independently unit-testable
with hand-computed expected values. Opening-area constants are loaded once from
seed_data/opening_area_constants.json at import time — config-driven defaults rather
than magic numbers baked into the formula, while callers can still override explicitly.
"""

import json
from pathlib import Path
from typing import NamedTuple, Protocol

_SEED_DATA_DIR = Path(__file__).resolve().parents[1] / "seed_data"
_constants = json.loads((_SEED_DATA_DIR / "opening_area_constants.json").read_text())
_material_applicability = json.loads((_SEED_DATA_DIR / "material_applicability.json").read_text())

DEFAULT_DOOR_OPENING_AREA_SQFT: float = _constants["door_opening_area_sqft"]
DEFAULT_WINDOW_OPENING_AREA_SQFT: float = _constants["window_opening_area_sqft"]


def calc_wall_perimeter_ft(length_ft: float, width_ft: float) -> float:
    """Full internal perimeter of a rectangular room."""
    return 2 * (length_ft + width_ft)


def calc_flooring_quantity(area_sqft: float, coverage_ratio: float = 1.0) -> float:
    """Flooring material quantity (sqft) = area_sqft * coverage_ratio."""
    return area_sqft * coverage_ratio


def calc_paint_plaster_quantity(
    length_ft: float,
    width_ft: float,
    ceiling_height_ft: float,
    door_count: int,
    window_count: int,
    door_opening_area_sqft: float = DEFAULT_DOOR_OPENING_AREA_SQFT,
    window_opening_area_sqft: float = DEFAULT_WINDOW_OPENING_AREA_SQFT,
) -> float:
    """Paint/plaster quantity (sqft) = perimeter * ceiling_height - door/window openings.

    Clamped at 0 so a room with more opening area than wall area (a data-entry
    error, not a real room) never produces a negative material quantity.
    """
    perimeter = calc_wall_perimeter_ft(length_ft, width_ft)
    gross_wall_area = perimeter * ceiling_height_ft
    openings_area = door_count * door_opening_area_sqft + window_count * window_opening_area_sqft
    return max(0.0, gross_wall_area - openings_area)


def calc_brickwork_concrete_quantity(
    wall_thickness_ft: float,
    ceiling_height_ft: float,
    length_ft: float,
    width_ft: float,
    wall_length_ft: float | None = None,
) -> float:
    """Brickwork/concrete volume (cft) = wall_thickness_ft * wall_length_ft * ceiling_height_ft.

    `wall_length_ft` is not a field in the locked v3 contract — if not supplied
    explicitly it defaults to the room's full perimeter (2*(length_ft+width_ft)),
    the same value used for paint/plaster. Brickwork and concrete both use this
    identical formula in this pass (separate material rows, different rates/units) —
    a known MVP simplification; the Stage 5 correction layer is the natural place to
    differentiate them once real historical data exists.
    """
    if wall_length_ft is None:
        wall_length_ft = calc_wall_perimeter_ft(length_ft, width_ft)
    return wall_thickness_ft * wall_length_ft * ceiling_height_ft


class RoomDimensions(Protocol):
    """Duck-typed — satisfied by the Room ORM model without importing it here,
    keeping this module free of any SQLAlchemy dependency."""

    length_ft: float
    width_ft: float
    ceiling_height_ft: float
    wall_thickness_ft: float
    area_sqft: float
    door_count: int
    window_count: int


class TheoreticalMaterialQuantity(NamedTuple):
    material_name: str
    quantity: float
    unit: str


def compute_room_theoretical_quantities(room: RoomDimensions) -> list[TheoreticalMaterialQuantity]:
    """Expands a room into its theoretical material quantities per
    seed_data/material_applicability.json. Every confirmed room gets the same
    material set in this pass — a documented MVP simplification (no per-room-type
    variation, e.g. balconies still get plaster) — extend the config to change that.
    """
    length_ft = float(room.length_ft)
    width_ft = float(room.width_ft)
    ceiling_height_ft = float(room.ceiling_height_ft)
    wall_thickness_ft = float(room.wall_thickness_ft)
    area_sqft = float(room.area_sqft)

    results: list[TheoreticalMaterialQuantity] = []
    for entry in _material_applicability["materials"]:
        formula = entry["formula"]
        if formula == "flooring":
            quantity = calc_flooring_quantity(area_sqft)
        elif formula == "paint_plaster":
            quantity = calc_paint_plaster_quantity(
                length_ft, width_ft, ceiling_height_ft, room.door_count, room.window_count
            )
        elif formula == "brickwork_concrete":
            quantity = calc_brickwork_concrete_quantity(
                wall_thickness_ft, ceiling_height_ft, length_ft, width_ft
            )
        else:
            raise ValueError(f"Unknown formula '{formula}' in material_applicability.json")
        results.append(TheoreticalMaterialQuantity(entry["material_name"], quantity, entry["unit"]))
    return results
