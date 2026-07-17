from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_job_or_404
from app.models.enums import JobStatus
from app.models.room import Room
from app.models.user import User
from app.schemas.constraints import ConstraintsRequest, ConstraintsResponse
from app.services.job_state_machine import transition
from app.services.rate_service import estimate_min_possible_cost, validate_material_overrides

router = APIRouter(tags=["constraints"])


@router.patch("/constraints/{job_id}", response_model=ConstraintsResponse)
def set_constraints(
    job_id: str,
    payload: ConstraintsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = get_job_or_404(job_id, db, current_user)
    # transition() itself enforces the precondition: valid from ROOMS_CONFIRMED
    # (first time) or CONSTRAINTS_SET/CALCULATED/EXPORTED (re-editing / what-if).
    transition(db, job, JobStatus.CONSTRAINTS_SET)

    warnings = validate_material_overrides(db, payload.material_overrides)

    rooms = db.query(Room).filter(Room.job_id == job_id).all()
    min_cost = estimate_min_possible_cost(db, rooms, job.location)
    if payload.budget_cap is not None and payload.budget_cap < min_cost:
        warnings.append(
            f"Budget cap Rs.{payload.budget_cap:,.2f} is below the estimated minimum "
            f"possible cost of Rs.{min_cost:,.2f} for the confirmed rooms — the final "
            "BOQ will likely exceed it."
        )

    job.budget_cap = payload.budget_cap
    job.material_overrides = [o.model_dump() for o in payload.material_overrides]
    db.add(job)
    db.commit()

    return ConstraintsResponse(
        budget_cap=payload.budget_cap,
        material_overrides=payload.material_overrides,
        warnings=warnings,
    )
