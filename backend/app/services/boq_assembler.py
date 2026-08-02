"""Stage 6 — BOQ assembly. Orchestrates quantity_engine (Stage 4) + rate_service
(Stage 4b) + correction_service (Stage 5) into persisted Material rows and the
locked v3 response contract.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import DomainError, NotFoundError
from app.models.enums import JobStatus
from app.models.job import Job
from app.models.material import Material
from app.models.room import Room
from app.schemas.boq import BOQConstraints, BOQResponse, BOQRoomOut, MaterialLine
from app.schemas.constraints import MaterialOverride
from app.schemas.room import Dimensions
from app.services.correction_service import get_active_correction_model
from app.services.exception_service import MaterialSnapshot, resolve_exception
from app.services.job_state_machine import assert_transition
from app.services.quantity_engine import compute_room_theoretical_quantities
from app.services.rate_service import get_rate


def calculate_job_boq(db: Session, job: Job) -> BOQResponse:
    # Validated (not mutated) here; job.status is only set to CALCULATED once the
    # whole calculation succeeds, alongside total_cost/calculated_at, in one commit —
    # so a failed calculation never leaves the job stuck in a CALCULATED-but-empty state.
    assert_transition(job, JobStatus.CALCULATED)

    rooms = db.query(Room).filter(Room.job_id == job.id).all()
    if not rooms:
        raise DomainError("No confirmed rooms to calculate")

    correction_model = get_active_correction_model(db)

    room_ids = [r.id for r in rooms]
    db.query(Material).filter(Material.room_id.in_(room_ids)).delete(synchronize_session=False)

    total_cost = 0.0
    for room in rooms:
        room_materials = compute_room_theoretical_quantities(room)

        # Exception agent: acts on this room's own material set only, after the
        # normal room-type-driven set is computed and before rates are looked up
        # (no point pricing a line that's about to be excluded). Exclusion drops
        # a material outright; an adjustment multiplier is tracked separately
        # rather than baked into room_materials, so theoretical_quantity keeps
        # meaning "what the pure formula said" — the same reason correction_factor
        # is a separate column rather than pre-multiplied into the quantity.
        exception_multipliers: dict[str, float] = {}
        if room.exception_text:
            result = resolve_exception(
                room.exception_text,
                [MaterialSnapshot(m.material_name, m.quantity, m.unit) for m in room_materials],
            )
            if result.exclude:
                room_materials = [m for m in room_materials if m.material_name not in result.exclude]
            exception_multipliers = result.adjustments
            room.exception_applied = result.note or None
        else:
            room.exception_applied = None
        db.add(room)

        for material_name, theoretical_quantity, unit in room_materials:
            try:
                rate_row = get_rate(db, material_name, unit, job.location)
            except NotFoundError:
                # No priced rate for this material/location — skip rather than
                # hard-failing the whole job's calculation over one unpriced item.
                continue

            correction = correction_model.predict(
                material_name=material_name,
                theoretical_quantity=theoretical_quantity,
                room_type=room.room_type.value,
            )
            exception_multiplier = exception_multipliers.get(material_name, 1.0)
            quantity = theoretical_quantity * correction.correction_factor * exception_multiplier
            rate_per_unit = float(rate_row.rate_per_unit)
            line_total_cost = quantity * rate_per_unit

            db.add(
                Material(
                    room_id=room.id,
                    material_name=material_name,
                    theoretical_quantity=theoretical_quantity,
                    correction_factor=correction.correction_factor,
                    correction_confidence=correction.correction_confidence,
                    quantity=quantity,
                    unit=unit,
                    rate_per_unit=rate_per_unit,
                    total_cost=line_total_cost,
                )
            )
            total_cost += line_total_cost

    job.status = JobStatus.CALCULATED
    job.total_cost = total_cost
    job.calculated_at = datetime.now(timezone.utc)
    db.add(job)
    db.commit()

    # Re-query fresh so room.materials reflects the just-committed rows.
    rooms = db.query(Room).filter(Room.job_id == job.id).all()
    db.refresh(job)

    return build_boq_response(job, rooms)


def build_boq_response(job: Job, rooms: list[Room]) -> BOQResponse:
    """Pure serialization: DB rows -> the exact nested v3 JSON, reconstructing
    `dimensions` from flattened columns."""
    room_outs = []
    for room in rooms:
        materials = [
            MaterialLine(
                material_name=m.material_name,
                theoretical_quantity=float(m.theoretical_quantity),
                correction_factor=float(m.correction_factor),
                correction_confidence=m.correction_confidence,
                quantity=float(m.quantity),
                unit=m.unit.value,
                rate_per_unit=float(m.rate_per_unit),
                total_cost=float(m.total_cost),
            )
            for m in room.materials
        ]
        room_outs.append(
            BOQRoomOut(
                room_id=room.id,
                room_name=room.room_name,
                room_name_raw=room.room_name_raw,
                room_type=room.room_type,
                area_sqft=float(room.area_sqft),
                dimensions=Dimensions(
                    length_ft=float(room.length_ft),
                    width_ft=float(room.width_ft),
                    ceiling_height_ft=float(room.ceiling_height_ft),
                    wall_thickness_ft=float(room.wall_thickness_ft),
                ),
                floor_type=room.floor_type,
                door_count=room.door_count,
                window_count=room.window_count,
                source=room.source,
                confirmed=room.confirmed,
                materials=materials,
                room_total_cost=sum(m.total_cost for m in materials),
                exception_text=room.exception_text,
                exception_applied=room.exception_applied,
            )
        )

    overrides = [MaterialOverride(**o) for o in (job.material_overrides or [])]

    return BOQResponse(
        project_name=job.project_name,
        location=job.location,
        generated_at=datetime.now(timezone.utc),
        constraints=BOQConstraints(
            budget_cap=float(job.budget_cap) if job.budget_cap is not None else None,
            material_overrides=overrides,
        ),
        rooms=room_outs,
        total_cost=float(job.total_cost) if job.total_cost is not None else 0.0,
        currency=job.currency,
    )
