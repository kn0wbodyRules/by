from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_job_or_404
from app.models.job import Job
from app.models.user import User
from app.schemas.boq import BOQResponse
from app.services.boq_assembler import calculate_job_boq

router = APIRouter(tags=["calculate"])


@router.post("/calculate/{job_id}", response_model=BOQResponse)
def calculate(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = get_job_or_404(job_id, db, current_user)

    # calculate_job_boq clears this job's material rows and re-inserts them. Two
    # calculates racing on the same job (a double-clicked Confirm, a client retry)
    # can both clear before either inserts, leaving the BOQ with every line item
    # duplicated and a doubled total. Locking the job row serialises them, so the
    # second call sees the first's committed state and the status check rejects it.
    db.query(Job).filter(Job.id == job.id).with_for_update().one()

    return calculate_job_boq(db, job)
