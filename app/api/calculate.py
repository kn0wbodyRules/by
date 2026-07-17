from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_job_or_404
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
    return calculate_job_boq(db, job)
