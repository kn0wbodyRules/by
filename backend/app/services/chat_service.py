"""Stage 7 — the QBQ chat orchestrator.

Free text in, a structured diff out. Gemini is used strictly as a *parser*: it
decides what the user is asking for and returns JSON, and this module decides
what may actually happen. The model never computes quantities or costs — those
stay with the deterministic engine — and it can only ever move the two levers the
Constraints screen already exposes.

Routing follows the brief:
  * a diff touching only ``constraints{}`` -> apply it and re-run Stage 4-6 in place
  * a diff touching ``rooms[]``            -> flag ``new_calculation_required`` so
                                              the UI restarts from Confirm
  * anything else                          -> answer from the current BOQ

Behind GEMINI_MOCK_MODE (or with no API key) a small keyword parser stands in, so
the endpoint stays useful offline and the tests never hit the network.
"""

import json
import logging
import re

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.enums import JobStatus
from app.models.job import Job
from app.models.room import Room
from app.schemas.chat import ChatResponse
from app.services.boq_assembler import build_boq_response, calculate_job_boq

logger = logging.getLogger("boq.chat")
settings = get_settings()

# Materials the rate table actually knows about. The model is told to map onto
# these exact names, so its output can be trusted as a lookup key.
KNOWN_MATERIALS = [
    "flooring_vitrified_tile",
    "wall_paint_emulsion",
    "cement_plaster",
    "brickwork",
    "concrete_rcc",
]

QBQ_SYSTEM_PROMPT = """
You are QBQ, the assistant inside a Bill of Quantity tool for civil engineers.

Classify the user's message and reply with ONLY a JSON object — no prose, no
markdown fences:

{{
  "intent": "adjust_constraints" | "modify_rooms" | "question" | "unclear",
  "budget_cap": <number or null>,
  "material_overrides": [{{"material_name": "...", "preferred_grade_or_brand": "..."}}],
  "reply": "<one or two sentences addressed to the user>"
}}

Rules:
- "adjust_constraints" — the user wants a different budget, or a different
  grade/brand for a material. Fill budget_cap and/or material_overrides.
- "modify_rooms" — the user wants to add, remove, rename or resize a room, or
  change its dimensions. Do NOT attempt the edit; just classify it.
- "question" — they are asking about the existing estimate. Answer it in "reply"
  using the BOQ context below, quoting real figures from it.
- "unclear" — you cannot tell. Ask a short clarifying question in "reply".
- material_name MUST be one of: {materials}
- budget_cap is a plain number in INR: no symbols, no separators. Interpret
  Indian units, so "5 lakh" is 500000 and "1.2 crore" is 12000000.
- Never invent quantities or costs. Only use figures from the BOQ context.
"""


def _boq_context(db: Session, job: Job) -> str:
    """A compact snapshot of the estimate for the model to reason over."""
    lines = [
        f"Project: {job.project_name}",
        f"Location: {job.location}",
        f"Status: {job.status.value}",
        f"Budget cap: {job.budget_cap if job.budget_cap is not None else 'not set'}",
        f"Total cost: {job.total_cost if job.total_cost is not None else 'not yet calculated'} {job.currency}",
    ]

    rooms = db.query(Room).filter(Room.job_id == job.id).all()
    lines.append(f"Rooms ({len(rooms)}):")
    for room in rooms:
        lines.append(
            f"  - {room.room_name} [{room.room_type.value}] "
            f"{room.length_ft}x{room.width_ft}ft, area {room.area_sqft} sqft"
        )
        for material in room.materials:
            lines.append(
                f"      {material.material_name}: {float(material.quantity):.2f} "
                f"{material.unit.value} @ {float(material.rate_per_unit):.2f} "
                f"= {float(material.total_cost):.2f}"
            )
    return "\n".join(lines)


def _parse_with_gemini(message: str, context: str) -> dict:
    from google import genai

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    prompt = (
        QBQ_SYSTEM_PROMPT.format(materials=", ".join(KNOWN_MATERIALS))
        + "\n\nCurrent BOQ context:\n"
        + context
        + f"\n\nUser message: {message}"
    )
    response = client.models.generate_content(model=settings.GEMINI_MODEL, contents=prompt)
    return _loads_lenient(response.text)


def _loads_lenient(text: str) -> dict:
    """Models sometimes wrap JSON in fences or add a stray sentence — pull out the
    first balanced object rather than failing the request over formatting."""
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


def _parse_offline(message: str) -> dict:
    """Keyword stand-in for when Gemini is unavailable. Deliberately conservative:
    it only claims an intent it can justify from the text."""
    text = message.lower()

    if re.search(r"\b(add|remove|delete|rename|resize)\b[^.]*\broom\b", text) or re.search(
        r"\broom\b[^.]*\b(add|remove|delete|rename|resize)\b", text
    ):
        return {
            "intent": "modify_rooms",
            "budget_cap": None,
            "material_overrides": [],
            "reply": "That changes the room list, so the estimate has to be rebuilt from the Confirm step.",
        }

    amount = _extract_amount(text)
    if amount is not None and re.search(r"budget|cap|spend|cost|price", text):
        return {
            "intent": "adjust_constraints",
            "budget_cap": amount,
            "material_overrides": [],
            "reply": f"Budget set to INR {amount:,.0f}.",
        }

    return {
        "intent": "unclear",
        "budget_cap": None,
        "material_overrides": [],
        "reply": (
            "I can change the budget or a material's grade, or answer questions about "
            'this estimate. Try: "set the budget to 5 lakh".'
        ),
    }


def _extract_amount(text: str) -> float | None:
    """Handles lakh/crore as well as plain numbers, since estimators write both."""
    match = re.search(r"(\d[\d,]*\.?\d*)\s*(lakh|lac|crore|cr|k)?", text)
    if not match:
        return None
    try:
        value = float(match.group(1).replace(",", ""))
    except ValueError:
        return None

    unit = match.group(2)
    multipliers = {
        "lakh": 100_000,
        "lac": 100_000,
        "crore": 10_000_000,
        "cr": 10_000_000,
        "k": 1_000,
    }
    if unit:
        value *= multipliers[unit]
    # A bare small number is far likelier to be a room count than a budget.
    return value if value >= 1000 else None


def handle_chat_message(db: Session, job: Job, message: str) -> ChatResponse:
    context = _boq_context(db, job)

    use_gemini = not settings.GEMINI_MOCK_MODE and bool(settings.GEMINI_API_KEY)
    if use_gemini:
        try:
            parsed = _parse_with_gemini(message, context)
        except Exception as exc:  # noqa: BLE001 — a chat reply must never 500 the app
            logger.warning("QBQ falling back to offline parsing: %s: %s", type(exc).__name__, exc)
            parsed = _parse_offline(message)
    else:
        parsed = _parse_offline(message)

    intent = str(parsed.get("intent", "unclear"))
    reply = str(parsed.get("reply") or "").strip()

    if intent == "modify_rooms":
        return ChatResponse(
            reply=reply or "That changes the rooms — reopen the room list to edit them.",
            new_calculation_required=True,
        )

    if intent == "adjust_constraints":
        return _apply_constraints(db, job, parsed, reply)

    return ChatResponse(
        reply=reply or "I couldn't work out what to change — could you rephrase?",
        new_calculation_required=False,
    )


def _apply_constraints(db: Session, job: Job, parsed: dict, reply: str) -> ChatResponse:
    """Persist a constraints diff and re-run the estimate in place."""
    changed = False

    budget = parsed.get("budget_cap")
    if isinstance(budget, (int, float)) and not isinstance(budget, bool) and budget > 0:
        job.budget_cap = float(budget)
        changed = True

    overrides = parsed.get("material_overrides") or []
    # Silently drop anything the rate table doesn't recognise rather than
    # persisting a name that will never resolve to a rate.
    accepted = [
        {
            "material_name": item["material_name"],
            "preferred_grade_or_brand": str(item.get("preferred_grade_or_brand", "")),
        }
        for item in overrides
        if isinstance(item, dict) and item.get("material_name") in KNOWN_MATERIALS
    ]
    if accepted:
        existing = {o["material_name"]: o for o in (job.material_overrides or [])}
        for override in accepted:
            existing[override["material_name"]] = override
        job.material_overrides = list(existing.values())
        changed = True

    if not changed:
        return ChatResponse(
            reply=reply or "I didn't find a budget or material grade to change in that.",
            new_calculation_required=False,
        )

    db.add(job)
    db.commit()

    # Only recalculate a job that has already been costed; doing it mid-flow
    # would jump the state machine.
    if job.status in (JobStatus.CALCULATED, JobStatus.EXPORTED):
        rooms = db.query(Room).filter(Room.job_id == job.id).all()
        boq = _recalculate(db, job, rooms)
        total = f"{job.currency} {boq.total_cost:,.2f}"
        over_budget = job.budget_cap is not None and boq.total_cost > float(job.budget_cap)
        suffix = (
            f" The estimate is {total}, which is over the new cap."
            if over_budget
            else f" The estimate is now {total}."
        )
        return ChatResponse(reply=(reply or "Updated.") + suffix, new_calculation_required=False)

    return ChatResponse(
        reply=reply or "Saved — it will be applied when the estimate runs.",
        new_calculation_required=False,
    )


def _recalculate(db: Session, job: Job, rooms: list[Room]):
    """Re-run the deterministic engine, falling back to the stored BOQ if that
    fails, so the user still gets a coherent answer."""
    try:
        return calculate_job_boq(db, job)
    except Exception as exc:  # noqa: BLE001
        logger.warning("QBQ recalculation failed, returning stored BOQ: %s", exc)
        return build_boq_response(job, rooms)
