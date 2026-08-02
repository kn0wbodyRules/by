"""Per-room exception agent: offline parsing, and the untrusted-output sanitizer.

The sanitizer tests are the important ones — they're what stops a hallucinated
or malicious model response from touching a material that doesn't exist in this
room, or applying a negative/absurd multiplier.
"""

import pytest

from app.services.exception_service import (
    MaterialSnapshot,
    _parse_offline,
    _sanitize,
    resolve_exception,
)

BEDROOM_MATERIALS = [
    MaterialSnapshot("flooring_vitrified_tile", 120.0, "sqft"),
    MaterialSnapshot("wall_paint_emulsion", 396.0, "sqft"),
    MaterialSnapshot("cement_plaster", 396.0, "sqft"),
    MaterialSnapshot("brickwork", 297.0, "cft"),
    MaterialSnapshot("concrete_rcc", 297.0, "cft"),
]
KNOWN_NAMES = {m.material_name for m in BEDROOM_MATERIALS}


# ------------------------------------------------------------------- top-level


def test_no_exception_text_is_a_no_op():
    result = resolve_exception("", BEDROOM_MATERIALS)
    assert result.exclude == frozenset()
    assert result.adjustments == {}


def test_no_materials_is_a_no_op():
    result = resolve_exception("skip plaster", [])
    assert result.exclude == frozenset()


# --------------------------------------------------------------- offline parser


def test_offline_excludes_plaster_on_skip_wording():
    parsed = _parse_offline("no plaster in this room", KNOWN_NAMES)
    assert parsed["exclude"] == ["cement_plaster"]
    assert parsed["adjustments"] == []


def test_offline_excludes_paint_on_dont_wording():
    parsed = _parse_offline("don't paint this one", KNOWN_NAMES)
    assert "wall_paint_emulsion" in parsed["exclude"]


def test_offline_adjusts_quantity_on_extra_percent_wording():
    parsed = _parse_offline("extra 20% tiles for cutting waste", KNOWN_NAMES)
    assert parsed["adjustments"] == [{"material_name": "flooring_vitrified_tile", "multiplier": 1.2}]
    assert parsed["exclude"] == []


def test_offline_grade_request_is_not_actionable():
    """The agent must not silently do nothing without saying why — a grade/brand
    request should come back with an explanatory note, not just empty lists."""
    parsed = _parse_offline("use premium tiles here", KNOWN_NAMES)
    assert parsed["exclude"] == []
    assert parsed["adjustments"] == []
    assert parsed["note"]


def test_offline_ignores_word_not_in_known_materials():
    # "brick" isn't mentioned, so brickwork must not be touched by an unrelated word.
    parsed = _parse_offline("no false ceiling in here", KNOWN_NAMES)
    assert parsed["exclude"] == []


# --------------------------------------------------- sanitizer (untrusted output)


def test_sanitize_drops_material_not_in_this_room():
    """The core protection: a hallucinated or cross-room material name must never
    reach the caller, or /calculate could try to exclude/adjust a line that was
    never computed for this room."""
    parsed = {
        "exclude": ["some_material_never_computed_here"],
        "adjustments": [{"material_name": "granite_slab", "multiplier": 1.5}],
        "note": "ok",
    }
    result = _sanitize(parsed, KNOWN_NAMES)
    assert result.exclude == frozenset()
    assert result.adjustments == {}


def test_sanitize_drops_negative_multiplier():
    parsed = {"exclude": [], "adjustments": [{"material_name": "cement_plaster", "multiplier": -0.5}]}
    result = _sanitize(parsed, KNOWN_NAMES)
    assert result.adjustments == {}


def test_sanitize_drops_non_numeric_multiplier():
    parsed = {"exclude": [], "adjustments": [{"material_name": "cement_plaster", "multiplier": "a lot"}]}
    result = _sanitize(parsed, KNOWN_NAMES)
    assert result.adjustments == {}


def test_sanitize_exclude_wins_over_adjustment_for_same_material():
    """If the model both excludes and adjusts the same line (contradictory,
    shouldn't happen, but untrusted output can say anything), removing the line
    entirely is the safer of the two outcomes."""
    parsed = {
        "exclude": ["cement_plaster"],
        "adjustments": [{"material_name": "cement_plaster", "multiplier": 1.3}],
    }
    result = _sanitize(parsed, KNOWN_NAMES)
    assert result.exclude == frozenset({"cement_plaster"})
    assert "cement_plaster" not in result.adjustments


def test_sanitize_accepts_valid_exclude_and_adjustment_together():
    parsed = {
        "exclude": ["wall_paint_emulsion"],
        "adjustments": [{"material_name": "flooring_vitrified_tile", "multiplier": 1.1}],
        "note": "Excluded paint, added 10% extra tiles.",
    }
    result = _sanitize(parsed, KNOWN_NAMES)
    assert result.exclude == frozenset({"wall_paint_emulsion"})
    assert result.adjustments == {"flooring_vitrified_tile": 1.1}
    assert result.note == "Excluded paint, added 10% extra tiles."


# ------------------------------------------------------ end-to-end (offline mode)


def test_resolve_exception_end_to_end_exclude(monkeypatch):
    from app.services import exception_service

    monkeypatch.setattr(exception_service.settings, "GEMINI_MOCK_MODE", True)
    result = resolve_exception("skip the plaster here", BEDROOM_MATERIALS)
    assert result.exclude == frozenset({"cement_plaster"})


def test_resolve_exception_gemini_failure_falls_back_to_offline(monkeypatch):
    """A broken/unreachable Gemini call must degrade to the offline parser, not
    raise — this runs inside /calculate and must never 500 it."""
    from app.services import exception_service

    monkeypatch.setattr(exception_service.settings, "GEMINI_MOCK_MODE", False)
    monkeypatch.setattr(exception_service.settings, "GEMINI_API_KEY", "test-key")

    def boom(text, materials):
        raise RuntimeError("gemini unreachable")

    monkeypatch.setattr(exception_service, "_parse_with_gemini", boom)
    result = resolve_exception("no plaster", BEDROOM_MATERIALS)
    assert result.exclude == frozenset({"cement_plaster"})
