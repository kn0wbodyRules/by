from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import JobStatus


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_name: str
    location: str
    status: JobStatus
    total_cost: float | None
    currency: str
    created_at: datetime
    updated_at: datetime


class UploadResponse(BaseModel):
    job_id: str
    status: JobStatus
