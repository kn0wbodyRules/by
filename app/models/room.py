from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, uuid_str
from app.models.enums import RoomSource, RoomType, room_source_enum, room_type_enum


class Room(Base, TimestampMixin):
    __tablename__ = "rooms"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)

    room_name: Mapped[str] = mapped_column(String, nullable=False)
    room_name_raw: Mapped[str] = mapped_column(String, nullable=False)
    room_type: Mapped[RoomType] = mapped_column(room_type_enum, nullable=False)

    area_sqft: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    length_ft: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    width_ft: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    ceiling_height_ft: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    wall_thickness_ft: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)

    floor_type: Mapped[str] = mapped_column(String, nullable=False, default="")
    door_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    window_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    source: Mapped[RoomSource] = mapped_column(room_source_enum, nullable=False)
    confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    job: Mapped["Job"] = relationship(back_populates="rooms")
    materials: Mapped[list["Material"]] = relationship(back_populates="room", cascade="all, delete-orphan")
