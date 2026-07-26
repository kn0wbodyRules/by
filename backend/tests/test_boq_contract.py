from app.models.enums import (
    CorrectionConfidence,
    JobStatus,
    MaterialUnit,
    RoomSource,
    RoomType,
)
from app.models.job import Job
from app.models.material import Material
from app.models.room import Room
from app.models.user import User
from app.services.boq_assembler import build_boq_response
from app.services.export_excel import generate_boq_excel
from app.services.export_pdf import generate_boq_pdf


def _make_job_with_room(db) -> tuple[Job, Room]:
    user = User(email="contract@example.com", hashed_password="x", is_verified=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    job = Job(
        user_id=user.id,
        status=JobStatus.CALCULATED,
        project_name="Contract Test House",
        location="Tamil Nadu",
        budget_cap=500000,
        material_overrides=[{"material_name": "flooring_vitrified_tile", "preferred_grade_or_brand": "Premium"}],
        total_cost=2550.0,
        currency="INR",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    room = Room(
        job_id=job.id,
        room_name="Common Toilet",
        room_name_raw="Attached Bath",
        room_type=RoomType.BATHROOM,
        area_sqft=30.0,
        length_ft=6.0,
        width_ft=5.0,
        ceiling_height_ft=9.0,
        wall_thickness_ft=0.5,
        floor_type="tile",
        door_count=1,
        window_count=0,
        source=RoomSource.MANUAL,
        confirmed=True,
    )
    db.add(room)
    db.commit()
    db.refresh(room)

    material = Material(
        room_id=room.id,
        material_name="flooring_vitrified_tile",
        theoretical_quantity=30.0,
        correction_factor=1.0,
        correction_confidence=CorrectionConfidence.FALLBACK,
        quantity=30.0,
        unit=MaterialUnit.SQFT,
        rate_per_unit=85.0,
        total_cost=2550.0,
    )
    db.add(material)
    db.commit()
    db.refresh(room)

    return job, room


def test_boq_response_top_level_keys_match_v3_contract(db):
    job, room = _make_job_with_room(db)
    boq = build_boq_response(job, [room])
    dumped = boq.model_dump()

    assert set(dumped.keys()) == {
        "project_name",
        "location",
        "generated_at",
        "constraints",
        "rooms",
        "total_cost",
        "currency",
    }


def test_boq_response_constraints_keys_match_v3_contract(db):
    job, room = _make_job_with_room(db)
    boq = build_boq_response(job, [room])
    dumped = boq.model_dump()

    assert set(dumped["constraints"].keys()) == {"budget_cap", "material_overrides"}
    assert set(dumped["constraints"]["material_overrides"][0].keys()) == {
        "material_name",
        "preferred_grade_or_brand",
    }


def test_boq_response_room_keys_match_v3_contract(db):
    job, room = _make_job_with_room(db)
    boq = build_boq_response(job, [room])
    dumped = boq.model_dump()

    room_out = dumped["rooms"][0]
    assert set(room_out.keys()) == {
        "room_id",
        "room_name",
        "room_name_raw",
        "room_type",
        "area_sqft",
        "dimensions",
        "floor_type",
        "door_count",
        "window_count",
        "source",
        "confirmed",
        "materials",
        "room_total_cost",
    }
    assert set(room_out["dimensions"].keys()) == {
        "length_ft",
        "width_ft",
        "ceiling_height_ft",
        "wall_thickness_ft",
    }


def test_boq_response_material_keys_match_v3_contract(db):
    job, room = _make_job_with_room(db)
    boq = build_boq_response(job, [room])
    dumped = boq.model_dump()

    material_out = dumped["rooms"][0]["materials"][0]
    assert set(material_out.keys()) == {
        "material_name",
        "theoretical_quantity",
        "correction_factor",
        "correction_confidence",
        "quantity",
        "unit",
        "rate_per_unit",
        "total_cost",
    }


def test_boq_response_values_are_correct(db):
    job, room = _make_job_with_room(db)
    boq = build_boq_response(job, [room])

    assert boq.project_name == "Contract Test House"
    assert boq.total_cost == 2550.0
    assert boq.rooms[0].room_total_cost == 2550.0
    assert boq.rooms[0].materials[0].material_name == "flooring_vitrified_tile"


def test_pdf_export_produces_valid_pdf_bytes(db):
    job, room = _make_job_with_room(db)
    boq = build_boq_response(job, [room])
    pdf_bytes = generate_boq_pdf(boq)

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 500


def test_excel_export_produces_valid_xlsx_bytes(db):
    job, room = _make_job_with_room(db)
    boq = build_boq_response(job, [room])
    xlsx_bytes = generate_boq_excel(boq)

    # .xlsx is a zip archive — PK magic number
    assert xlsx_bytes.startswith(b"PK")
    assert len(xlsx_bytes) > 500


def test_csv_export_renders_real_rows(db):
    """Generates the actual file rather than only checking status codes — the
    first CSV implementation called .value on `unit`, which is a plain str in the
    BOQ schema even though room_type and correction_confidence are Enums, and a
    status-only test sailed straight past the resulting 500."""
    from app.services.export_csv import generate_boq_csv

    job, room = _make_job_with_room(db)
    boq = build_boq_response(job, [room])

    text = generate_boq_csv(boq).decode("utf-8-sig")
    lines = [line for line in text.splitlines() if line.strip()]

    assert any(line.startswith("# Project,Contract Test House") for line in lines)

    header = next(line for line in lines if line.startswith("room_name,"))
    assert header.split(",") == [
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

    data_row = next(line for line in lines if line.startswith("Common Toilet,"))
    cells = data_row.split(",")
    # Enum columns must serialise to their values, not "RoomType.BATHROOM".
    assert cells[1] == "bathroom"
    assert cells[3] == "flooring_vitrified_tile"
    assert cells[8] == "sqft"

    assert lines[-1].startswith("TOTAL,")
