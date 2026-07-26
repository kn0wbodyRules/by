"""Stage 2b embedding-escalation tests.

These never call the real Gemini API — the reference/query embeddings are stubbed with
deterministic vectors so the cosine + threshold + escalation logic is tested offline.
Live end-to-end behaviour and threshold calibration live in tools/calibrate_room_embed.py.
"""

import pytest

from app.config import get_settings
from app.models.enums import RoomType
from app.services import room_classifier, room_classifier_embedding as rce


@pytest.fixture()
def stub_embeddings(monkeypatch):
    """Replace _embed with a deterministic fake: each room type gets a distinct
    one-hot-ish basis vector; a query maps to its type's vector (near-perfect match)
    or a neutral vector (matches nothing above threshold)."""
    types_in_order = list(rce.REFERENCE_PHRASES.keys())
    dim = len(types_in_order)

    # phrase -> its owning room type, for building reference vectors
    phrase_to_type = {p: rt for rt, ps in rce.REFERENCE_PHRASES.items() for p in ps}

    query_map: dict[str, str] = {}

    def _basis(room_type: RoomType) -> list[float]:
        return [1.0 if t is room_type else 0.0 for t in types_in_order]

    def fake_embed(texts: list[str]) -> list[list[float]]:
        out = []
        for text in texts:
            if text in phrase_to_type:  # a reference phrase
                out.append(_basis(phrase_to_type[text]))
            elif text in query_map:  # a query we've set up to match a type
                out.append(_basis(RoomType(query_map[text])))
            else:  # unknown query -> neutral vector, cosine ~ equal & low to all bases
                out.append([1.0] * dim)
        return out

    monkeypatch.setattr(rce, "_embed", fake_embed)
    monkeypatch.setattr(rce, "_reference_vectors", None)  # force recompute with stub
    # Enable the layer (real settings may be in mock mode for the test session).
    settings = get_settings()
    monkeypatch.setattr(settings, "GEMINI_MOCK_MODE", False)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    return query_map


def test_embedding_matches_when_above_threshold(stub_embeddings):
    stub_embeddings["chill zone"] = "living_room"
    result = rce.classify_by_embedding("chill zone")
    assert result is not None
    room_type, score = result
    assert room_type is RoomType.LIVING_ROOM
    assert score >= get_settings().ROOM_EMBED_MATCH_THRESHOLD


def test_embedding_returns_none_below_threshold(stub_embeddings):
    # Unknown query -> neutral vector, cosine to every basis is low -> below threshold.
    assert rce.classify_by_embedding("quantum reactor bay") is None


def test_embedding_disabled_in_mock_mode(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "GEMINI_MOCK_MODE", True)
    assert rce.classify_by_embedding("chill zone") is None


def test_embedding_never_raises_on_api_failure(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "GEMINI_MOCK_MODE", False)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(rce, "_reference_vectors", None)

    def boom(texts):
        raise RuntimeError("gemini down")

    monkeypatch.setattr(rce, "_embed", boom)
    # Must degrade to None, not propagate — room ingestion must never crash on this.
    assert rce.classify_by_embedding("chill zone") is None


def test_escalation_prefers_keyword_and_skips_embedding(monkeypatch):
    """A name the keyword layer already places must NOT trigger an embedding call."""
    called = False

    def tripwire(_name):
        nonlocal called
        called = True
        return None

    monkeypatch.setattr(room_classifier, "classify_room_type_escalated", room_classifier.classify_room_type_escalated)
    import app.services.room_classifier_embedding as emb
    monkeypatch.setattr(emb, "classify_by_embedding", tripwire)

    result = room_classifier.classify_room_type_escalated("Master Bedroom")
    assert result is RoomType.BEDROOM
    assert called is False


def test_escalation_falls_back_to_embedding_for_other(monkeypatch):
    """A name the keyword layer can't place (OTHER) must consult the embedding layer."""
    import app.services.room_classifier_embedding as emb
    monkeypatch.setattr(emb, "classify_by_embedding", lambda name: (RoomType.LIVING_ROOM, 0.95))

    result = room_classifier.classify_room_type_escalated("chill zone")
    assert result is RoomType.LIVING_ROOM


def test_escalation_stays_other_when_embedding_unsure(monkeypatch):
    import app.services.room_classifier_embedding as emb
    monkeypatch.setattr(emb, "classify_by_embedding", lambda name: None)

    result = room_classifier.classify_room_type_escalated("quantum reactor bay")
    assert result is RoomType.OTHER
