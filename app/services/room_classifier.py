"""Stage 2b — rule-based room-type classifier.

Maps free-text room_name_raw into the fixed room_type enum via word-boundary
keyword matching. Word-boundary (not naive substring) matching is what correctly
separates e.g. "hall" from "hallway", and prevents "washroom" from false-matching a
bare "wash" token. Multi-word/specific phrases are checked ahead of generic single
tokens, and groups are checked in the priority order below — first match wins.

Baseline covers ~80% per the design brief; ambiguous remainder is a documented
future escalation to TF-IDF + logistic regression, not built here. area_sqft/
aspect_ratio/door_count/window_count are accepted but UNUSED — the deliberate seam
for that future model so callers never need to change.
"""

import re

from app.models.enums import RoomType

# Ordered: most specific/multi-word phrases first, generic single tokens later.
ROOM_TYPE_KEYWORDS: list[tuple[RoomType, list[str]]] = [
    (
        RoomType.BATHROOM,
        ["attached bath", "powder room", "bathroom", "washroom", "restroom", "toilet", "wc"],
    ),
    (RoomType.POOJA_ROOM, ["prayer room", "pooja", "puja"]),
    (RoomType.KITCHEN, ["kitchen cum dining", "modular kitchen", "kitchen"]),
    (RoomType.UTILITY, ["wash area", "service area", "utility", "laundry"]),
    (RoomType.STORE_ROOM, ["store room", "storage", "store"]),
    (RoomType.BALCONY, ["sit-out", "sitout", "balcony", "terrace", "deck"]),
    (RoomType.CORRIDOR, ["hallway", "corridor", "passage", "lobby", "foyer"]),
    (RoomType.BEDROOM, ["master bedroom", "guest room", "bed room", "bedroom", "mbr"]),
    (RoomType.LIVING_ROOM, ["living room", "drawing room", "family room", "lounge", "hall"]),
]


def _matches_keyword(text: str, keyword: str) -> bool:
    pattern = r"\b" + re.escape(keyword) + r"\b"
    return re.search(pattern, text, re.IGNORECASE) is not None


def classify_room_type(
    room_name_raw: str,
    area_sqft: float | None = None,
    aspect_ratio: float | None = None,
    door_count: int | None = None,
    window_count: int | None = None,
) -> RoomType:
    """Pure keyword baseline — deterministic, offline, no external calls. Returns OTHER
    when nothing matches. The extra feature args are the unused seam described above."""
    text = room_name_raw or ""
    for room_type, keywords in ROOM_TYPE_KEYWORDS:
        for keyword in keywords:
            if _matches_keyword(text, keyword):
                return room_type
    return RoomType.OTHER


def classify_room_type_escalated(
    room_name_raw: str,
    area_sqft: float | None = None,
    aspect_ratio: float | None = None,
    door_count: int | None = None,
    window_count: int | None = None,
) -> RoomType:
    """Stage 2b entry point used by the pipeline: keyword baseline first, then escalate
    to the Gemini embedding classifier only for the ambiguous remainder the keywords
    can't place (i.e. when the baseline returns OTHER). Falls back to OTHER if the
    embedding layer is disabled (mock mode / no key) or not confident enough."""
    keyword_result = classify_room_type(
        room_name_raw,
        area_sqft=area_sqft,
        aspect_ratio=aspect_ratio,
        door_count=door_count,
        window_count=window_count,
    )
    if keyword_result is not RoomType.OTHER:
        return keyword_result

    # Lazy import keeps the pure keyword path free of the google-genai dependency and
    # keeps this module unit-testable fully offline.
    from app.services.room_classifier_embedding import classify_by_embedding

    match = classify_by_embedding(room_name_raw)
    return match[0] if match is not None else RoomType.OTHER


def compute_aspect_ratio(length_ft: float, width_ft: float) -> float:
    """>=1.0, longer side over shorter side. Long-thin rooms skew corridor/utility —
    exposed for future classifier-feature use, not consumed by the rule-based path."""
    if length_ft <= 0 or width_ft <= 0:
        return 1.0
    long_side, short_side = max(length_ft, width_ft), min(length_ft, width_ft)
    return long_side / short_side
