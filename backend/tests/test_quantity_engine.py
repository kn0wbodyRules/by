from dataclasses import dataclass

import pytest

from app.services.quantity_engine import (
    calc_brickwork_concrete_quantity,
    calc_flooring_quantity,
    calc_paint_plaster_quantity,
    calc_wall_perimeter_ft,
    compute_room_theoretical_quantities,
    materials_for_room_type,
)


@dataclass
class _FakeRoom:
    room_type: str
    length_ft: float
    width_ft: float
    ceiling_height_ft: float
    wall_thickness_ft: float
    area_sqft: float
    door_count: int
    window_count: int


def test_wall_perimeter():
    assert calc_wall_perimeter_ft(10, 12) == 44


def test_flooring_default_coverage():
    assert calc_flooring_quantity(area_sqft=120) == 120


def test_flooring_with_coverage_ratio():
    assert calc_flooring_quantity(area_sqft=120, coverage_ratio=0.95) == pytest.approx(114.0)


def test_paint_plaster_hand_computed():
    # room 10x12, ceiling 9ft, 1 door (21 sqft), 2 windows (12 sqft each)
    # perimeter = 2*(10+12) = 44; gross = 44*9 = 396
    # openings = 1*21 + 2*12 = 45; net = 396 - 45 = 351
    result = calc_paint_plaster_quantity(
        length_ft=10,
        width_ft=12,
        ceiling_height_ft=9,
        door_count=1,
        window_count=2,
        door_opening_area_sqft=21,
        window_opening_area_sqft=12,
    )
    assert result == pytest.approx(351.0)


def test_paint_plaster_no_openings():
    # perimeter = 2*(8+8) = 32; gross = 32*8 = 256; no openings
    result = calc_paint_plaster_quantity(
        length_ft=8,
        width_ft=8,
        ceiling_height_ft=8,
        door_count=0,
        window_count=0,
        door_opening_area_sqft=21,
        window_opening_area_sqft=12,
    )
    assert result == pytest.approx(256.0)


def test_paint_plaster_clamped_at_zero():
    # a tiny room where openings exceed gross wall area must not go negative
    result = calc_paint_plaster_quantity(
        length_ft=1,
        width_ft=1,
        ceiling_height_ft=1,
        door_count=1,
        window_count=1,
        door_opening_area_sqft=21,
        window_opening_area_sqft=12,
    )
    assert result == 0.0


def test_brickwork_concrete_default_wall_length_uses_perimeter():
    # wall_thickness 0.75ft, ceiling 9ft, perimeter defaults to 2*(10+12)=44
    # 0.75 * 44 * 9 = 297.0
    result = calc_brickwork_concrete_quantity(
        wall_thickness_ft=0.75, ceiling_height_ft=9, length_ft=10, width_ft=12
    )
    assert result == pytest.approx(297.0)


def test_brickwork_concrete_explicit_wall_length_overrides_perimeter():
    # 0.75 * 50 * 9 = 337.5 — explicit wall_length_ft wins over the perimeter default
    result = calc_brickwork_concrete_quantity(
        wall_thickness_ft=0.75,
        ceiling_height_ft=9,
        length_ft=10,
        width_ft=12,
        wall_length_ft=50,
    )
    assert result == pytest.approx(337.5)


def test_compute_room_theoretical_quantities_bedroom_gets_all_five_materials():
    room = _FakeRoom(
        room_type="bedroom",
        length_ft=10,
        width_ft=12,
        ceiling_height_ft=9,
        wall_thickness_ft=0.75,
        area_sqft=120,
        door_count=1,
        window_count=2,
    )
    results = compute_room_theoretical_quantities(room)
    material_names = {r.material_name for r in results}
    assert material_names == {
        "flooring_vitrified_tile",
        "wall_paint_emulsion",
        "cement_plaster",
        "brickwork",
        "concrete_rcc",
    }
    # paint and plaster share the identical quantity (same formula, per MVP simplification)
    by_name = {r.material_name: r for r in results}
    assert by_name["wall_paint_emulsion"].quantity == by_name["cement_plaster"].quantity
    assert by_name["brickwork"].quantity == by_name["concrete_rcc"].quantity
    assert by_name["flooring_vitrified_tile"].quantity == pytest.approx(120.0)
    assert by_name["flooring_vitrified_tile"].unit == "sqft"
    assert by_name["brickwork"].unit == "cft"


def test_materials_for_room_type_bathroom_skips_paint():
    materials = materials_for_room_type("bathroom")
    assert "wall_paint_emulsion" not in materials
    assert "cement_plaster" in materials  # base layer stays, only paint is skipped
    assert "flooring_vitrified_tile" in materials


def test_materials_for_room_type_balcony_skips_paint_and_plaster():
    materials = materials_for_room_type("balcony")
    assert "wall_paint_emulsion" not in materials
    assert "cement_plaster" not in materials
    assert set(materials) == {"flooring_vitrified_tile", "brickwork", "concrete_rcc"}


def test_materials_for_room_type_unrecognised_falls_back_to_full_set():
    """A room_type not present in the config (or a future enum value the config
    hasn't been updated for) must not silently under-compute."""
    assert set(materials_for_room_type("nonexistent_type")) == {
        "flooring_vitrified_tile",
        "wall_paint_emulsion",
        "cement_plaster",
        "brickwork",
        "concrete_rcc",
    }


def test_compute_room_theoretical_quantities_bathroom_excludes_paint():
    room = _FakeRoom(
        room_type="bathroom",
        length_ft=6,
        width_ft=5,
        ceiling_height_ft=9,
        wall_thickness_ft=0.5,
        area_sqft=30,
        door_count=1,
        window_count=0,
    )
    results = compute_room_theoretical_quantities(room)
    material_names = {r.material_name for r in results}
    assert "wall_paint_emulsion" not in material_names
    assert material_names == {"flooring_vitrified_tile", "cement_plaster", "brickwork", "concrete_rcc"}


def test_compute_room_theoretical_quantities_balcony_only_flooring_and_structural():
    room = _FakeRoom(
        room_type="balcony",
        length_ft=8,
        width_ft=4,
        ceiling_height_ft=9,
        wall_thickness_ft=0.5,
        area_sqft=32,
        door_count=1,
        window_count=0,
    )
    results = compute_room_theoretical_quantities(room)
    material_names = {r.material_name for r in results}
    assert material_names == {"flooring_vitrified_tile", "brickwork", "concrete_rcc"}
