"""Stage 7 — chat orchestrator. Reduced scope this pass: validates job ownership and
returns a canned acknowledgement referencing the job's current total cost, giving the
frontend a real response shape to integrate against now. Full LLM-diff-into-
constraints{}-or-rooms[] logic (parsing free text into a structured diff, then either
re-running Stage 4-6 in place or flagging new_calculation_required) is a documented
follow-up, not built here.
"""

from app.models.job import Job
from app.schemas.chat import ChatResponse


def handle_chat_message(job: Job, message: str) -> ChatResponse:
    total_cost_str = (
        f"{job.currency} {float(job.total_cost):,.2f}" if job.total_cost is not None else "not yet calculated"
    )
    reply = (
        f'Thanks for your message about "{job.project_name}". The current estimated '
        f"total cost is {total_cost_str}. Full conversational editing of constraints "
        "and rooms is coming soon — for now, use the Constraints screen to adjust "
        "budget/material grades, or edit rooms and recalculate."
    )
    return ChatResponse(reply=reply, new_calculation_required=False)
