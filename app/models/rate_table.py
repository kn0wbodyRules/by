from datetime import date

from sqlalchemy import Date, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid_str
from app.models.enums import MaterialUnit, material_unit_enum


class RateTable(Base, TimestampMixin):
    """Pricing master — (material_name, unit, location) -> rate_per_unit.

    Pluggable/config-driven: seeded from JSON, not hardcoded in code. A new location
    is new rows, not a rewrite.
    """

    __tablename__ = "rate_table"
    __table_args__ = (UniqueConstraint("material_name", "unit", "location", name="uq_rate_material_unit_location"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    material_name: Mapped[str] = mapped_column(String, index=True, nullable=False)
    unit: Mapped[MaterialUnit] = mapped_column(material_unit_enum, nullable=False)
    rate_per_unit: Mapped[float] = mapped_column(nullable=False)
    location: Mapped[str] = mapped_column(String, nullable=False, default="Tamil Nadu")
    source_label: Mapped[str] = mapped_column(String, nullable=False, default="")
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
