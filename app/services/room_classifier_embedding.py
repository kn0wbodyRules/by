"""Stage 2b escalation — Gemini embedding-based room-type classification.

The rule-based keyword baseline (``room_classifier.classify_room_type``) handles the
common, clearly-labelled cases for free and instantly. This module covers the
ambiguous remainder: free-text / colloquial labels ("chill zone", "hangout spot",
"prayer corner") that share no keyword with the enum but are semantically close to a
known room type.

How it works: a fixed set of reference phrases per room type is embedded once via the
same Gemini API key already used for Vision, then cached in memory. An unknown room
name is embedded and matched to the nearest reference phrase by cosine similarity
(nearest-neighbour, not centroid — a category like living_room legitimately spans
"formal drawing room" and "chill zone", which a single averaged vector would blur).
Below ``ROOM_EMBED_MATCH_THRESHOLD`` the guess is not trusted and the room stays
OTHER — the same "don't guess when unsure" philosophy as the correction-factor
confidence gating.

Degrades safely: in GEMINI_MOCK_MODE, with no API key, or on any API error, returns
None so the caller keeps its existing (keyword) result rather than crashing room
ingestion — mirroring room_normalizer's partial-success stance. Pure-Python cosine
(no numpy) keeps this dependency-light on Python 3.14.
"""

import logging
import math

from app.config import get_settings
from app.models.enums import RoomType

logger = logging.getLogger("boq.room_classifier_embedding")
settings = get_settings()

# Reference phrases per room type. Varied phrasing per type gives the nearest-neighbour
# match more surface area, and deliberately includes colloquial / Indian-residential
# vocabulary the keyword list doesn't cover. OTHER is intentionally absent: it isn't a
# semantic category, it's "nothing matched confidently" (below-threshold -> OTHER).
REFERENCE_PHRASES: dict[RoomType, list[str]] = {
    RoomType.BEDROOM: [
        "bedroom", "master bedroom", "guest bedroom", "children's room", "room for sleeping",
    ],
    RoomType.KITCHEN: [
        "kitchen", "modular kitchen", "cooking area", "kitchen cum dining",
    ],
    RoomType.BATHROOM: [
        "bathroom", "toilet", "washroom", "powder room", "restroom", "attached bath",
    ],
    RoomType.LIVING_ROOM: [
        "living room", "drawing room", "family room", "lounge", "sitting room",
        "tv room", "chill zone", "hangout area",
    ],
    RoomType.UTILITY: [
        "utility room", "wash area", "laundry room", "service area",
    ],
    RoomType.POOJA_ROOM: [
        "pooja room", "prayer room", "puja room", "worship space", "meditation room",
    ],
    RoomType.STORE_ROOM: [
        "store room", "storage room", "pantry", "stock room",
    ],
    RoomType.BALCONY: [
        "balcony", "sit-out", "terrace", "deck", "veranda", "open sitting area",
    ],
    RoomType.CORRIDOR: [
        "corridor", "passage", "hallway", "lobby", "foyer", "walkway",
    ],
}

# (room_type, phrase) pairs flattened for nearest-neighbour matching.
_FLAT_REFERENCES: list[tuple[RoomType, str]] = [
    (room_type, phrase)
    for room_type, phrases in REFERENCE_PHRASES.items()
    for phrase in phrases
]

# Cached reference embeddings, computed once on first escalation. A benign double-embed
# under a first-call race is harmless (idempotent), so no lock — kept simple.
_reference_vectors: list[tuple[RoomType, list[float]]] | None = None


def _embed(texts: list[str]) -> list[list[float]]:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    result = client.models.embed_content(
        model=settings.GEMINI_EMBED_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(
            task_type="SEMANTIC_SIMILARITY",
            output_dimensionality=settings.ROOM_EMBED_DIM,
        ),
    )
    return [embedding.values for embedding in result.embeddings]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _ensure_reference_vectors() -> list[tuple[RoomType, list[float]]] | None:
    global _reference_vectors
    if _reference_vectors is None:
        phrases = [phrase for _, phrase in _FLAT_REFERENCES]
        vectors = _embed(phrases)
        _reference_vectors = [
            (room_type, vec) for (room_type, _), vec in zip(_FLAT_REFERENCES, vectors)
        ]
    return _reference_vectors


def classify_by_embedding(room_name_raw: str) -> tuple[RoomType, float] | None:
    """Return (room_type, similarity) for the nearest reference phrase if the match
    clears ROOM_EMBED_MATCH_THRESHOLD, else None.

    None means "not confident / not available" — the caller keeps its existing keyword
    result. Never raises: any API/availability failure degrades to None.
    """
    if settings.GEMINI_MOCK_MODE or not settings.GEMINI_API_KEY:
        return None
    text = (room_name_raw or "").strip()
    if not text:
        return None
    try:
        references = _ensure_reference_vectors()
        if not references:
            return None
        query_vec = _embed([text])[0]
        best_type: RoomType | None = None
        best_score = -1.0
        for room_type, ref_vec in references:
            score = _cosine(query_vec, ref_vec)
            if score > best_score:
                best_score, best_type = score, room_type
        if best_type is not None and best_score >= settings.ROOM_EMBED_MATCH_THRESHOLD:
            return best_type, best_score
        return None
    except Exception as exc:  # noqa: BLE001 — availability failure must not crash ingestion
        logger.warning("embedding classification failed for %r: %s", text, exc)
        return None
