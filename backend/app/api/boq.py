from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_job_or_404
from app.models.enums import JobStatus
from app.models.room import Room
from app.models.user import User
from app.schemas.boq import BOQResponse
from app.services.boq_assembler import build_boq_response
from app.services.export_excel import generate_boq_excel
from app.services.export_pdf import generate_boq_pdf
from app.services.job_state_machine import assert_transition, require_status

router = APIRouter(tags=["boq"])


@router.get("/boq/{job_id}", response_model=BOQResponse)
def get_boq(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = get_job_or_404(job_id, db, current_user)
    require_status(job, JobStatus.CALCULATED, JobStatus.EXPORTED)
    rooms = db.query(Room).filter(Room.job_id == job_id).all()
    return build_boq_response(job, rooms)


@router.get("/export/{job_id}")
def export_boq(
    job_id: str,
    format: Literal["pdf", "excel"],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = get_job_or_404(job_id, db, current_user)
    require_status(job, JobStatus.CALCULATED, JobStatus.EXPORTED)
    rooms = db.query(Room).filter(Room.job_id == job_id).all()
    boq = build_boq_response(job, rooms)

    if format == "pdf":
        content = generate_boq_pdf(boq)
        media_type = "application/pdf"
        filename = f"boq_{job_id}.pdf"
    else:
        content = generate_boq_excel(boq)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"boq_{job_id}.xlsx"

    if job.status != JobStatus.EXPORTED:
        assert_transition(job, JobStatus.EXPORTED)
        job.status = JobStatus.EXPORTED
        job.exported_at = datetime.now(timezone.utc)
        db.add(job)
        db.commit()

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
