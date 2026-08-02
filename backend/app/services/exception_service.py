"""Per-room exception agent — runs automatically as the last step of /calculate,
after the deterministic engine has computed a room's normal material set.

Scope is deliberately narrow. For a room with exception_text set, the agent may
only:
  * EXCLUDE one of that room's already-computed materials entirely
  * SCALE one of them by a stated multiplier (e.g. "extra 20% tiles for cutting
    waste" -> 1.2x that material's quantity)

It may NOT invent a new material, a new rate, or a material grade/brand swap
("use premium tiles") — grade/brand changes are the existing global
material_overrides mechanism (constraints screen / QBQ chat), not this. Keeping
the agent's power to "which of these known lines, and by how much" — never
"invent a number" — is what makes its output safe to apply without a human
reviewing every case.

Mirrors chat_service.py's pattern: Gemini as parser only, this module decides
what the parsed intent is allowed to do. Same GEMINI_MOCK_MODE-aware fallback to
an offline keyword parser, so /calculate never depends on the network to run.
"""

import json
import logging
import re
from dataclasses import dataclass

from app.config import get_settings

logger = logging.getLogger("boq.exception_agent")
settings = get_settings()

EXCEPTION_SYSTEM_PROMPT = """
You are adjusting the material list for ONE room in a Bill of Quantity, based on
a special requirement the user wrote for that room only.

Current materials in this room (name: quantity unit):
{materials_summary}

Room's special requirement: "{exception_text}"

Reply with ONLY a JSON object — no prose, no markdown fences:
{{
  "exclude": ["<material_name>", ...],
  "adjustments": [{{"material_name": "<material_name>", "multiplier": <number>}}],
  "note": "<one short sentence summarising what you changed and why, for the user>"
}}

Rules:
- material_name in "exclude" and "adjustments" MUST be one of the materials listed
  above, spelled exactly as shown. Never reference a material not in that list.
- Use "exclude" when the requirement means this room should not have that
  material at all (e.g. "no plaster here", "skip the false ceiling" if false
  ceiling were tracked — if the requirement refers to something not in the list,
  do not exclude anything for it).
- Use "adjustments" for a stated quantity change (extra wastage, thicker
  application, etc.) — multiplier is relative to the current quantity: 1.2 = 20%
  more, 0.8 = 20% less. Never below 0.
- Do NOT use this to change a material's grade, brand, or quality tier — say so
  in "note" instead (e.g. "premium tiles need a grade override in Constraints,
  not a room exception") and leave exclude/adjustments empty for that request.
- If the requirement doesn't map to anything actionable here, return empty
  exclude/adjustments and explain why in "note".
"""


@dataclass(frozen=True)
class MaterialSnapshot:
    """The subset of a computed material line the agent is allowed to see/touch."""

    material_name: str
    quantity: float
    unit: str


@dataclass(frozen=True)
class ExceptionResult:
    exclude: frozenset[str]
    adjustments: dict[str, float]  # material_name -> multiplier
    note: str


def resolve_exception(exception_text: str, materials: list[MaterialSnapshot]) -> ExceptionResult:
    """Never raises — a broken exception agent must not break /calculate. Any
    failure degrades to "no change, explain why" rather than a 500."""
    text = (exception_text or "").strip()
    if not text or not materials:
        return ExceptionResult(exclude=frozenset(), adjustments={}, note="")

    known_names = {m.material_name for m in materials}

    use_gemini = not settings.GEMINI_MOCK_MODE and bool(settings.GEMINI_API_KEY)
    if use_gemini:
        try:
            parsed = _parse_with_gemini(text, materials)
        except Exception as exc:  # noqa: BLE001 — a failed parse must not 500 /calculate
            logger.warning(
                "Exception agent falling back to offline parsing: %s: %s", type(exc).__name__, exc
            )
            parsed = _parse_offline(text, known_names)
    else:
        parsed = _parse_offline(text, known_names)

    return _sanitize(parsed, known_names)


def _sanitize(parsed: dict, known_names: set[str]) -> ExceptionResult:
    """The model's output is untrusted — drop anything referencing a material
    outside this room's actual list rather than trusting it at face value."""
    exclude = {
        name for name in (parsed.get("exclude") or []) if isinstance(name, str) and name in known_names
    }

    adjustments: dict[str, float] = {}
    for item in parsed.get("adjustments") or []:
        if not isinstance(item, dict):
            continue
        name = item.get("material_name")
        multiplier = item.get("multiplier")
        if (
            isinstance(name, str)
            and name in known_names
            and name not in exclude  # excluding wins over adjusting the same line
            and isinstance(multiplier, (int, float))
            and not isinstance(multiplier, bool)
            and multiplier >= 0
        ):
            adjustments[name] = float(multiplier)

    note = str(parsed.get("note") or "").strip()
    return ExceptionResult(exclude=frozenset(exclude), adjustments=adjustments, note=note)


def _parse_with_gemini(exception_text: str, materials: list[MaterialSnapshot]) -> dict:
    from google import genai

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    summary = "\n".join(f"  - {m.material_name}: {m.quantity:.2f} {m.unit}" for m in materials)
    prompt = EXCEPTION_SYSTEM_PROMPT.format(materials_summary=summary, exception_text=exception_text)
    response = client.models.generate_content(model=settings.GEMINI_MODEL, contents=prompt)
    return _loads_lenient(response.text)


def _loads_lenient(text: str) -> dict:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).rsplit("```", 1)[0].strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.S)
        if not match:
            raise
        return json.loads(match.group(0))


# Materials a bare keyword match can confidently exclude offline. Keyed by
# synonym -> real material_name, so "paint"/"painting" both hit the right line.
_EXCLUDE_SYNONYMS: dict[str, str] = {
    "paint": "wall_paint_emulsion",
    "painting": "wall_paint_emulsion",
    "plaster": "cement_plaster",
    "plastering": "cement_plaster",
    "brick": "brickwork",
    "brickwork": "brickwork",
    "concrete": "concrete_rcc",
    "flooring": "flooring_vitrified_tile",
    "floor": "flooring_vitrified_tile",
    "tile": "flooring_vitrified_tile",
    "tiles": "flooring_vitrified_tile",
}

_SKIP_WORDS = re.compile(r"\b(no|skip|without|exclude|omit|don't|dont|not)\b", re.IGNORECASE)
_EXTRA_WORDS = re.compile(r"\b(extra|more|additional)\b", re.IGNORECASE)
_PERCENT = re.compile(r"(\d+)\s*%")


def _parse_offline(text: str, known_names: set[str]) -> dict:
    """Keyword stand-in for when Gemini is unavailable. Deliberately conservative
    — only claims an exclude/adjustment it can point to a specific word for."""
    lower = text.lower()
    exclude: list[str] = []
    adjustments: list[dict] = []

    wants_skip = bool(_SKIP_WORDS.search(lower))
    wants_extra = bool(_EXTRA_WORDS.search(lower))
    percent_match = _PERCENT.search(lower)

    for word, material_name in _EXCLUDE_SYNONYMS.items():
        if material_name not in known_names or material_name in exclude:
            continue
        if not re.search(rf"\b{re.escape(word)}\b", lower):
            continue
        if wants_skip:
            exclude.append(material_name)
        elif wants_extra and percent_match:
            pct = int(percent_match.group(1))
            adjustments.append({"material_name": material_name, "multiplier": 1 + pct / 100})

    if exclude:
        note = f"Excluded {', '.join(exclude)} per this room's note."
    elif adjustments:
        note = "Adjusted quantity per this room's note."
    else:
        note = (
            "Couldn't map this note to a specific material change "
            "(grade/brand requests belong in Constraints, not here)."
        )

    return {"exclude": exclude, "adjustments": adjustments, "note": note}
