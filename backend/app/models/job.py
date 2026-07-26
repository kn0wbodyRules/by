from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, uuid_str
from app.models.enums import JobStatus, job_status_enum


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    status: Mapped[JobStatus] = mapped_column(job_status_enum, default=JobStatus.UPLOADED, nullable=False)

    project_name: Mapped[str] = mapped_column(String, nullable=False, default="Untitled Project")
    location: Mapped[str] = mapped_column(String, nullable=False, default="Tamil Nadu")
    uploaded_file_path: Mapped[str | None] = mapped_column(String, nullable=True)

    budget_cap: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    material_overrides: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)

    total_cost: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String, nullable=False, default="INR")

    calculated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="jobs")
    rooms: Mapped[list["Room"]] = relationship(back_populates="job", cascade="all, delete-orphan")
