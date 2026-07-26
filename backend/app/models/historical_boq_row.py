from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, uuid_str, utcnow


class HistoricalBOQRow(Base):
    """Future ML training data — real historical BOQ sheets (Kolathu-site format:
    theoretical vs actual quantity/rate). Empty at seed time; populated as real
    project data is sourced. correction_factor = actual_qty / theoretical_qty is
    computed from this table once enough rows exist per (room_type, material).

    job_id/room_id use SET NULL (not CASCADE) on delete — training data must survive
    even if the originating job is later deleted.
    """

    __tablename__ = "historical_boq_rows"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)

    item: Mapped[str] = mapped_column(String, nullable=False)
    dims: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    theoretical_qty: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    actual_qty: Mapped[float | None] = mapped_column(Numeric(12, 3), nullable=True)
    boq_rate: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    actual_rate: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)

    job_id: Mapped[str | None] = mapped_column(ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    room_id: Mapped[str | None] = mapped_column(ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
