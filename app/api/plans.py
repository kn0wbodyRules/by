from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_job_or_404
from app.models.job import Job
from app.models.user import User
from app.schemas.job import JobOut

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("", response_model=list[JobOut])
def list_plans(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(Job)
        .filter(Job.user_id == current_user.id)
        .order_by(Job.created_at.desc())
        .all()
    )


@router.delete("/{plan_id}")
def delete_plan(
    plan_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = get_job_or_404(plan_id, db, current_user)
    db.delete(job)
    db.commit()
    return {"message": "Plan deleted"}
