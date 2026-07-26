from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, uuid_str, utcnow
from app.models.enums import CorrectionConfidence, MaterialUnit, correction_confidence_enum, material_unit_enum


class Material(Base):
    """Per-room BOQ line item — the array nested under each room in the v3 contract.

    No FK to rate_table: rate_per_unit is snapshotted at /calculate time so a later
    rate_table update (real PWD SOR replacing placeholders) doesn't retroactively
    change already-calculated BOQs.
    """

    __tablename__ = "materials"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    room_id: Mapped[str] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)

    material_name: Mapped[str] = mapped_column(String, nullable=False)
    theoretical_quantity: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    correction_factor: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False, default=1.0)
    correction_confidence: Mapped[CorrectionConfidence] = mapped_column(
        correction_confidence_enum, nullable=False, default=CorrectionConfidence.FALLBACK
    )
    quantity: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    unit: Mapped[MaterialUnit] = mapped_column(material_unit_enum, nullable=False)
    rate_per_unit: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    total_cost: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    room: Mapped["Room"] = relationship(back_populates="materials")
