import pytest

from app.models.enums import RoomType
from app.services.room_classifier import classify_room_type, compute_aspect_ratio


@pytest.mark.parametrize(
    "room_name_raw,expected",
    [
        ("Bathroom 1", RoomType.BATHROOM),
        ("Attached Bath", RoomType.BATHROOM),
        ("Common Toilet", RoomType.BATHROOM),
        ("Washroom", RoomType.BATHROOM),
        ("Pooja Room", RoomType.POOJA_ROOM),
        ("Puja", RoomType.POOJA_ROOM),
        ("Modular Kitchen", RoomType.KITCHEN),
        ("Kitchen", RoomType.KITCHEN),
        ("Wash Area", RoomType.UTILITY),
        ("Utility", RoomType.UTILITY),
        ("Store Room", RoomType.STORE_ROOM),
        ("Storage", RoomType.STORE_ROOM),
        ("Balcony", RoomType.BALCONY),
        ("Sit-out", RoomType.BALCONY),
        ("Corridor", RoomType.CORRIDOR),
        ("Hallway", RoomType.CORRIDOR),
        ("Master Bedroom", RoomType.BEDROOM),
        ("Bedroom 2", RoomType.BEDROOM),
        ("MBR", RoomType.BEDROOM),
        ("Living Room", RoomType.LIVING_ROOM),
        ("Hall", RoomType.LIVING_ROOM),
        ("Drawing Room", RoomType.LIVING_ROOM),
        ("Server Closet", RoomType.OTHER),
        ("", RoomType.OTHER),
    ],
)
def test_classify_room_type(room_name_raw, expected):
    assert classify_room_type(room_name_raw) == expected


def test_hallway_does_not_match_hall_livingroom_keyword():
    # "hallway" must resolve to CORRIDOR, not LIVING_ROOM, despite containing "hall"
    # as a substring — word-boundary matching plus corridor's priority over
    # living_room is what makes this work.
    assert classify_room_type("Hallway") == RoomType.CORRIDOR


def test_washroom_does_not_match_wash_area_utility_keyword():
    # "washroom" must resolve to BATHROOM, not UTILITY, despite loosely resembling
    # "wash" — the utility keyword is the full phrase "wash area", which washroom
    # does not contain as a word-boundary-delimited match.
    assert classify_room_type("Washroom") == RoomType.BATHROOM


def test_carwash_area_does_not_false_positive_utility():
    # "carwash area" contains "wash area" as a raw substring but not at a word
    # boundary (the 'w' of 'wash' is preceded by 'r', not a boundary) — must not
    # match UTILITY via naive substring containment.
    assert classify_room_type("Carwash Area") == RoomType.OTHER


def test_case_insensitive():
    assert classify_room_type("BEDROOM") == RoomType.BEDROOM
    assert classify_room_type("bedroom") == RoomType.BEDROOM


def test_compute_aspect_ratio():
    assert compute_aspect_ratio(10, 5) == pytest.approx(2.0)
    assert compute_aspect_ratio(5, 10) == pytest.approx(2.0)
    assert compute_aspect_ratio(8, 8) == pytest.approx(1.0)
