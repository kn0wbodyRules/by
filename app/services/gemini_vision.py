"""Gemini Vision room detection from an uploaded floor-plan photo.

GEMINI_ROOM_DETECTION_PROMPT is the isolated prompt-editing point for whoever owns
prompt engineering — everything below it is plumbing. call_gemini_vision returns
UNTRUSTED, unvalidated JSON; all type-coercion and validation happens downstream in
room_normalizer.normalize_gemini_rooms, never here.

Behind GEMINI_MOCK_MODE (or when no GEMINI_API_KEY is set), returns a fixture
response so /detect-rooms is fully testable before real Gemini credentials exist.
"""

import json

from app.config import get_settings
from app.core.exceptions import DomainError

settings = get_settings()

GEMINI_ROOM_DETECTION_PROMPT = """
You are analyzing a residential floor plan image. Identify every distinct room shown.

For each room, return a JSON object with these fields:
- room_name: string — the label printed on the plan, or your best guess if unlabeled
- length_ft: number — the room's length in feet
- width_ft: number — the room's width in feet
- floor_type: string — best guess (e.g. "tile", "wood", "concrete") if not labeled
- door_count: integer — number of doors into the room
- window_count: integer — number of windows in the room

Do not include ceiling_height_ft or wall_thickness_ft — these are not visible in a
2D floor plan photo and will be filled in with defaults for the user to confirm.

Respond with ONLY a JSON array of these objects. No prose, no markdown code fences.
""".strip()


class GeminiAPIError(DomainError):
    status_code = 502


def _mock_response() -> list[dict]:
    return [
        {
            "room_name": "Master Bedroom",
            "length_ft": 14,
            "width_ft": 12,
            "floor_type": "tile",
            "door_count": 1,
            "window_count": 2,
        },
        {
            "room_name": "Kitchen",
            "length_ft": 10,
            "width_ft": 8,
            "floor_type": "tile",
            "door_count": 1,
            "window_count": 1,
        },
        {
            "room_name": "Attached Bath",
            "length_ft": 6,
            "width_ft": 5,
            "floor_type": "tile",
            "door_count": 1,
            "window_count": 0,
        },
        {
            "room_name": "Living Room",
            "length_ft": 16,
            "width_ft": 14,
            "floor_type": "tile",
            "door_count": 1,
            "window_count": 3,
        },
    ]


def _strip_markdown_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


def call_gemini_vision(image_bytes: bytes, mime_type: str) -> list[dict]:
    if settings.GEMINI_MOCK_MODE or not settings.GEMINI_API_KEY:
        return _mock_response()

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                GEMINI_ROOM_DETECTION_PROMPT,
            ],
        )
        rows = json.loads(_strip_markdown_fences(response.text))
        if not isinstance(rows, list):
            raise ValueError("Gemini response was not a JSON array")
        return rows
    except Exception as exc:
        raise GeminiAPIError(f"Gemini Vision call failed: {exc}") from exc
