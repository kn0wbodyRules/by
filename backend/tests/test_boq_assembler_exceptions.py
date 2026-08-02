"""Integration coverage for the exception agent as actually wired into
calculate_job_boq — proving exclude/adjust reach real, persisted Material rows
and total_cost, not just the isolated exception_service unit tests.
"""

import pytest

from app.models.enums import JobStatus, RoomSource, RoomType
from app.models.job import Job
from app.models.room import Room
from app.models.user import User
from app.services.boq_assembler import calculate_job_boq


def _make_job(db, *, exception_text: str | None = None) -> tuple[Job, Room]:
    user = User(email=f"exc-{exception_text!r}@example.com", hashed_password="x", is_verified=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    job = Job(
        user_id=user.id,
        status=JobStatus.CONSTRAINTS_SET,
        project_name="Exception Test House",
        location="Tamil Nadu",
        currency="INR",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    room = Room(
        job_id=job.id,
        room_name="Hall-1",
        room_name_raw="Hall-1",
        room_type=RoomType.BEDROOM,  # full 5-material set, so exclusion is visible
        area_sqft=120.0,
        length_ft=10.0,
        width_ft=12.0,
        ceiling_height_ft=9.0,
        wall_thickness_ft=0.75,
        floor_type="tile",
        door_count=1,
        window_count=2,
        source=RoomSource.MANUAL,
        confirmed=True,
        exception_text=exception_text,
    )
    db.add(room)
    db.commit()
    db.refresh(room)

    return job, room


def test_calculate_without_exception_text_produces_all_five_materials(db):
    job, room = _make_job(db, exception_text=None)
    boq = calculate_job_boq(db, job)

    room_out = boq.rooms[0]
    assert {m.material_name for m in room_out.materials} == {
        "flooring_vitrified_tile",
        "wall_paint_emulsion",
        "cement_plaster",
        "brickwork",
        "concrete_rcc",
    }
    assert room_out.exception_text is None
    assert room_out.exception_applied is None


def test_calculate_with_exclusion_removes_the_material_and_its_cost(db):
    job, room = _make_job(db, exception_text="no plaster in this room please")
    boq = calculate_job_boq(db, job)
    room_out = boq.rooms[0]
    material_names = {m.material_name for m in room_out.materials}

    assert "cement_plaster" not in material_names
    assert material_names == {
        "flooring_vitrified_tile",
        "wall_paint_emulsion",
        "brickwork",
        "concrete_rcc",
    }
    # The note must actually explain what happened, not just be truthy.
    assert room_out.exception_applied is not None
    assert "cement_plaster" in room_out.exception_applied

    # Persisted on the Room row too, not just the response — GET /boq reads this
    # back later without re-running the agent.
    db.refresh(room)
    assert room.exception_applied == room_out.exception_applied


def test_calculate_with_adjustment_scales_quantity_and_cost(db):
    baseline_job, baseline_room = _make_job(db, exception_text=None)
    baseline_boq = calculate_job_boq(db, baseline_job)
    baseline_flooring = next(
        m for m in baseline_boq.rooms[0].materials if m.material_name == "flooring_vitrified_tile"
    )

    adjusted_job, adjusted_room = _make_job(db, exception_text="extra 20% tiles for cutting waste")
    adjusted_boq = calculate_job_boq(db, adjusted_job)
    adjusted_flooring = next(
        m for m in adjusted_boq.rooms[0].materials if m.material_name == "flooring_vitrified_tile"
    )

    assert adjusted_flooring.quantity == pytest.approx(baseline_flooring.quantity * 1.2)
    assert adjusted_flooring.total_cost == pytest.approx(baseline_flooring.total_cost * 1.2)
    # theoretical_quantity records the pre-adjustment figure — the multiplier
    # only affects the final quantity actually priced, same pattern as the
    # correction_factor column.
    assert adjusted_flooring.theoretical_quantity == pytest.approx(baseline_flooring.theoretical_quantity)


def test_calculate_exception_never_touches_a_material_outside_this_room(db):
    """A bathroom's material set (no wall_paint_emulsion, per Stage 4 room-type
    rules) means "no paint" has nothing to exclude — the agent must not error or
    invent a line that was never computed for this room."""
    user = User(email="bath-exc@example.com", hashed_password="x", is_verified=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    job = Job(
        user_id=user.id, status=JobStatus.CONSTRAINTS_SET,
        project_name="Bath Exception Test", location="Tamil Nadu", currency="INR",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    room = Room(
        job_id=job.id, room_name="Bath-1", room_name_raw="Bath-1",
        room_type=RoomType.BATHROOM, area_sqft=30.0, length_ft=6.0, width_ft=5.0,
        ceiling_height_ft=9.0, wall_thickness_ft=0.5, floor_type="tile",
        door_count=1, window_count=0, source=RoomSource.MANUAL, confirmed=True,
        exception_text="no paint in the bathroom",
    )
    db.add(room)
    db.commit()

    boq = calculate_job_boq(db, job)
    material_names = {m.material_name for m in boq.rooms[0].materials}
    assert "wall_paint_emulsion" not in material_names  # already true from room_type alone
    assert material_names == {"flooring_vitrified_tile", "cement_plaster", "brickwork", "concrete_rcc"}
