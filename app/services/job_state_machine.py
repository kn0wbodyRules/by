"""Stage 0 — job state machine. Every endpoint that mutates or reads a job checks/
enforces this, rejecting out-of-order calls with a clear 409 instead of silently
producing garbage or a raw 500.
"""

from sqlalchemy.orm import Session

from app.core.exceptions import InvalidStateTransitionError
from app.models.enums import JobStatus
from app.models.job import Job

VALID_TRANSITIONS: dict[JobStatus, set[JobStatus]] = {
    JobStatus.UPLOADED: {JobStatus.ROOMS_DETECTED, JobStatus.ROOMS_MANUAL},
    JobStatus.ROOMS_DETECTED: {JobStatus.ROOMS_CONFIRMED},
    JobStatus.ROOMS_MANUAL: {JobStatus.ROOMS_CONFIRMED},
    JobStatus.ROOMS_CONFIRMED: {JobStatus.CONSTRAINTS_SET},
    # Loop-back edges: constraints can be re-edited / recalculated / what-if'd after
    # the fact — this is also the chat orchestrator's "re-evaluate in place" path.
    JobStatus.CONSTRAINTS_SET: {JobStatus.CALCULATED, JobStatus.CONSTRAINTS_SET},
    JobStatus.CALCULATED: {JobStatus.EXPORTED, JobStatus.CONSTRAINTS_SET},
    JobStatus.EXPORTED: {JobStatus.CONSTRAINTS_SET},
}


def assert_transition(job: Job, target: JobStatus) -> None:
    allowed = VALID_TRANSITIONS.get(job.status, set())
    if target not in allowed:
        raise InvalidStateTransitionError(
            f"Cannot move job from '{job.status.value}' to '{target.value}'"
        )


def transition(db: Session, job: Job, target: JobStatus) -> Job:
    assert_transition(job, target)
    job.status = target
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def require_status(job: Job, *allowed: JobStatus) -> None:
    """Read-only precondition check — does not mutate job.status."""
    if job.status not in allowed:
        allowed_str = ", ".join(s.value for s in allowed)
        raise InvalidStateTransitionError(
            f"Job status is '{job.status.value}'; this action requires one of: {allowed_str}"
        )
