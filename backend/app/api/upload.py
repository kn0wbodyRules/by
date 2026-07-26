import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.config import get_settings
from app.core.exceptions import DomainError
from app.models.enums import JobStatus
from app.models.job import Job
from app.models.user import User
from app.schemas.job import UploadResponse

router = APIRouter(tags=["upload"])
settings = get_settings()

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf", ".dxf", ".dwg"}


@router.post("/upload", response_model=UploadResponse)
def upload_floor_plan(
    file: UploadFile = File(...),
    project_name: str = Form("Untitled Project"),
    location: str = Form("Tamil Nadu"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise DomainError(
            f"Unsupported file type '{extension}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    saved_name = f"{uuid.uuid4()}{extension}"
    saved_path = upload_dir / saved_name
    with saved_path.open("wb") as out:
        out.write(file.file.read())

    job = Job(
        user_id=current_user.id,
        status=JobStatus.UPLOADED,
        project_name=project_name,
        location=location,
        uploaded_file_path=str(saved_path),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    return UploadResponse(job_id=job.id, status=job.status)
