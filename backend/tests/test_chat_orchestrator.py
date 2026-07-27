"""Stage 7 QBQ orchestrator.

Gemini is stubbed throughout — these assert the routing and the guardrails around
what a parsed message is allowed to change, not the model's own wording.
"""

import pytest

from app.models.enums import JobStatus, RoomSource, RoomType
from app.models.job import Job
from app.models.room import Room
from app.models.user import User
from app.services import chat_service
from app.services.chat_service import handle_chat_message


@pytest.fixture()
def job(db) -> Job:
    user = User(email="chat@example.com", hashed_password="x", is_verified=True)
    db.add(user)
    db.commit()

    job = Job(
        user_id=user.id,
        status=JobStatus.CALCULATED,
        project_name="Chat Test House",
        location="Tamil Nadu",
        budget_cap=200000,
        material_overrides=[],
        total_cost=126121.0,
        currency="INR",
    )
    db.add(job)
    db.commit()

    db.add(
        Room(
            job_id=job.id,
            room_name="Room 1",
            room_name_raw="Room 1",
            room_type=RoomType.BEDROOM,
            area_sqft=100.0,
            length_ft=10.0,
            width_ft=10.0,
            ceiling_height_ft=10.0,
            wall_thickness_ft=0.75,
            floor_type="tile",
            door_count=1,
            window_count=1,
            source=RoomSource.MANUAL,
            confirmed=True,
        )
    )
    db.commit()
    db.refresh(job)
    return job


def _stub_gemini(monkeypatch, payload: dict):
    monkeypatch.setattr(chat_service.settings, "GEMINI_MOCK_MODE", False)
    monkeypatch.setattr(chat_service.settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(chat_service, "_parse_with_gemini", lambda message, context: payload)


# --------------------------------------------------------------------- routing


def test_room_change_flags_restart_and_changes_nothing(db, job, monkeypatch):
    _stub_gemini(
        monkeypatch,
        {"intent": "modify_rooms", "budget_cap": None, "material_overrides": [], "reply": "Rooms change."},
    )
    before = float(job.budget_cap)

    result = handle_chat_message(db, job, "add a kitchen")

    assert result.new_calculation_required is True
    assert float(job.budget_cap) == before


def test_budget_change_is_persisted_and_recalculated(db, job, monkeypatch):
    _stub_gemini(
        monkeypatch,
        {"intent": "adjust_constraints", "budget_cap": 500000, "material_overrides": [], "reply": "Budget updated."},
    )

    result = handle_chat_message(db, job, "set the budget to 5 lakh")

    assert result.new_calculation_required is False
    assert float(job.budget_cap) == 500000
    # A recalculated job reports its new total back to the user.
    assert "INR" in result.reply


def test_question_answers_without_mutating_the_job(db, job, monkeypatch):
    _stub_gemini(
        monkeypatch,
        {
            "intent": "question",
            "budget_cap": None,
            "material_overrides": [],
            "reply": "Brickwork is the largest line at INR 28,500.",
        },
    )
    before = float(job.budget_cap)

    result = handle_chat_message(db, job, "what costs the most?")

    assert "brickwork" in result.reply.lower()
    assert result.new_calculation_required is False
    assert float(job.budget_cap) == before


# ------------------------------------------------------------------ guardrails


def test_unknown_material_override_is_dropped(db, job, monkeypatch):
    """The model can only move levers the rate table understands — a made-up
    material would never resolve to a rate."""
    _stub_gemini(
        monkeypatch,
        {
            "intent": "adjust_constraints",
            "budget_cap": None,
            "material_overrides": [
                {"material_name": "unobtainium", "preferred_grade_or_brand": "Premium"},
                {"material_name": "brickwork", "preferred_grade_or_brand": "Wienerberger"},
            ],
            "reply": "Updated.",
        },
    )

    handle_chat_message(db, job, "use premium unobtainium and Wienerberger bricks")

    names = {o["material_name"] for o in (job.material_overrides or [])}
    assert names == {"brickwork"}


def test_gemini_failure_falls_back_instead_of_raising(db, job, monkeypatch):
    monkeypatch.setattr(chat_service.settings, "GEMINI_MOCK_MODE", False)
    monkeypatch.setattr(chat_service.settings, "GEMINI_API_KEY", "test-key")

    def boom(message, context):
        raise RuntimeError("gemini unavailable")

    monkeypatch.setattr(chat_service, "_parse_with_gemini", boom)

    # Must degrade to the offline parser — a chat reply should never 500 the app.
    result = handle_chat_message(db, job, "set the budget to 8 lakh")
    assert float(job.budget_cap) == 800000
    assert result.reply


def test_malformed_model_output_is_recovered(monkeypatch):
    """Models wrap JSON in fences or add stray prose; that shouldn't fail the request."""
    payload = chat_service._loads_lenient('```json\n{"intent": "question", "reply": "hi"}\n```')
    assert payload["intent"] == "question"

    payload = chat_service._loads_lenient('Sure! {"intent": "unclear", "reply": "hm"} hope that helps')
    assert payload["intent"] == "unclear"


# -------------------------------------------------------------- offline parser


@pytest.mark.parametrize(
    "message,expected",
    [
        ("set the budget to 5 lakh", 500000),
        ("increase the budget to 1.2 crore", 12000000),
        ("cap the cost at 250000", 250000),
    ],
)
def test_offline_parser_reads_indian_amounts(message, expected):
    parsed = chat_service._parse_offline(message)
    assert parsed["intent"] == "adjust_constraints"
    assert parsed["budget_cap"] == expected


def test_offline_parser_routes_room_edits(db, job):
    parsed = chat_service._parse_offline("please add a pooja room")
    assert parsed["intent"] == "modify_rooms"


def test_offline_parser_admits_uncertainty():
    parsed = chat_service._parse_offline("hello there")
    assert parsed["intent"] == "unclear"
    assert parsed["budget_cap"] is None
