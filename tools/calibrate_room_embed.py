"""Calibration harness for the Stage 2b embedding room-classifier threshold.

Run this whenever the reference phrases, embedding model, or output dimension change,
to re-check that ROOM_EMBED_MATCH_THRESHOLD still cleanly separates genuine (but
keyword-missed) room names from non-rooms that should stay OTHER.

    python -m tools.calibrate_room_embed

Prints the nearest room type + cosine score for each probe, plus the min score among
"should match" and max score among "should stay OTHER" — the threshold belongs between
those two numbers. Makes real Gemini API calls, so needs a live GEMINI_API_KEY.
"""

from app.config import get_settings
from app.services import room_classifier_embedding as rce

# Creative / colloquial names the keyword baseline misses but that map to a real type.
SHOULD_MATCH = [
    ("chill zone", "living_room"), ("hangout spot", "living_room"),
    ("prayer corner", "pooja_room"), ("god room", "pooja_room"),
    ("cooking space", "kitchen"), ("place to cook", "kitchen"),
    ("kids sleeping area", "bedroom"), ("wc", "bathroom"), ("loo", "bathroom"),
    ("dhobi area", "utility"), ("clothes washing", "utility"),
    ("open sit out", "balcony"), ("junk room", "store_room"), ("walk through", "corridor"),
]
# Genuinely not one of the room-type enum values — must stay OTHER.
SHOULD_OTHER = [
    "car parking", "garden", "swimming pool", "office cabin", "shop", "staircase",
]


def _nearest(name: str, references):
    query = rce._embed([name])[0]
    best_type, best_score = None, -1.0
    for room_type, ref_vec in references:
        score = rce._cosine(query, ref_vec)
        if score > best_score:
            best_score, best_type = score, room_type
    return best_type.value, best_score


def main() -> None:
    settings = get_settings()
    if settings.GEMINI_MOCK_MODE or not settings.GEMINI_API_KEY:
        raise SystemExit("Set GEMINI_API_KEY and GEMINI_MOCK_MODE=false to calibrate.")

    references = rce._ensure_reference_vectors()
    print(f"threshold currently = {settings.ROOM_EMBED_MATCH_THRESHOLD}\n")

    print("=== SHOULD MATCH ===")
    match_scores = []
    for name, expected in SHOULD_MATCH:
        got, score = _nearest(name, references)
        match_scores.append(score)
        flag = "OK" if got == expected else f"WRONG(exp {expected})"
        print(f"  {name:22} -> {got:12} {score:.3f}  {flag}")

    print("=== SHOULD STAY OTHER ===")
    other_scores = []
    for name in SHOULD_OTHER:
        got, score = _nearest(name, references)
        other_scores.append(score)
        print(f"  {name:22} -> {got:12} {score:.3f}")

    print(f"\nmin 'should match' score : {min(match_scores):.3f}")
    print(f"max 'should other' score : {max(other_scores):.3f}")
    print("-> threshold should sit between those two.")


if __name__ == "__main__":
    main()
