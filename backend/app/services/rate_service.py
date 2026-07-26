"""Stage 4b — rate table lookups against the pluggable/config-driven pricing master."""

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.rate_table import RateTable
from app.models.room import Room
from app.schemas.constraints import MaterialOverride
from app.services.quantity_engine import compute_room_theoretical_quantities


def get_rate(db: Session, material_name: str, unit: str, location: str = "Tamil Nadu") -> RateTable:
    rate = (
        db.query(RateTable)
        .filter(
            RateTable.material_name == material_name,
            RateTable.unit == unit,
            RateTable.location == location,
        )
        .first()
    )
    if not rate:
        raise NotFoundError(f"No rate found for material '{material_name}' ({unit}) in {location}")
    return rate


def validate_material_overrides(db: Session, overrides: list[MaterialOverride]) -> list[str]:
    """Warns (does not hard-fail) about overrides naming materials the rate table
    doesn't know about, rather than rejecting the whole constraints update."""
    known_names = {row[0] for row in db.query(RateTable.material_name).distinct()}
    warnings = []
    for override in overrides:
        if override.material_name not in known_names:
            warnings.append(
                f"Material override '{override.material_name}' does not match any known "
                "material and will be ignored."
            )
    return warnings


def estimate_min_possible_cost(db: Session, rooms: list[Room], location: str) -> float:
    """Sums theoretical_quantity * rate_per_unit across all rooms with
    correction_factor=1.0 (the uncorrected baseline) — a lower-bound sanity check for
    whether a budget_cap is realistically reachable, not a final cost figure (the
    real /calculate pass applies the Stage 5 correction layer on top of this)."""
    total = 0.0
    for room in rooms:
        for material_name, quantity, unit in compute_room_theoretical_quantities(room):
            rate = (
                db.query(RateTable)
                .filter(
                    RateTable.material_name == material_name,
                    RateTable.unit == unit,
                    RateTable.location == location,
                )
                .first()
            )
            if rate:
                total += quantity * float(rate.rate_per_unit)
    return total
