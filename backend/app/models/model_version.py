from datetime import date

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid_str
from app.models.enums import ModelVersionStatus, model_version_status_enum


class ModelVersion(Base, TimestampMixin):
    """Model registry — one row per trained correction-factor model. The inference
    layer (correction_service.get_active_correction_model) reads the row with
    status='active' at call time; a retrain only takes effect once explicitly
    promoted here after passing the leave-one-project-out validation gate.
    """

    __tablename__ = "model_versions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    model_version: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    trained_on_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    validation_score: Mapped[float | None] = mapped_column(nullable=True)
    status: Mapped[ModelVersionStatus] = mapped_column(
        model_version_status_enum, nullable=False, default=ModelVersionStatus.ACTIVE
    )
