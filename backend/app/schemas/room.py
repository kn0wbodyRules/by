from pydantic import BaseModel, Field

from app.models.enums import RoomSource, RoomType


class Dimensions(BaseModel):
    length_ft: float
    width_ft: float
    ceiling_height_ft: float
    wall_thickness_ft: float


class ManualRoomInput(BaseModel):
    room_name: str
    length_ft: float = Field(gt=0)
    width_ft: float = Field(gt=0)
    ceiling_height_ft: float = Field(gt=0)
    wall_thickness_ft: float = Field(gt=0)
    floor_type: str = ""
    door_count: int = Field(0, ge=0)
    window_count: int = Field(0, ge=0)


class ManualRoomsRequest(BaseModel):
    rooms: list[ManualRoomInput]


class RoomOut(BaseModel):
    room_id: str
    room_name: str
    room_name_raw: str
    room_type: RoomType
    area_sqft: float
    dimensions: Dimensions
    floor_type: str
    door_count: int
    window_count: int
    source: RoomSource
    confirmed: bool


class DetectRoomsResponse(BaseModel):
    rooms: list[RoomOut]
    rejected_count: int
    rejections: list[dict]


class RoomEdit(BaseModel):
    """Confirm-screen edits — all fields optional except room_id; only fields the
    user actually changed need to be sent. room_type edits here are how user
    corrections to the rule-based classifier get captured (Stage 2b)."""

    room_id: str
    room_name: str | None = None
    room_type: RoomType | None = None
    length_ft: float | None = Field(default=None, gt=0)
    width_ft: float | None = Field(default=None, gt=0)
    ceiling_height_ft: float | None = Field(default=None, gt=0)
    wall_thickness_ft: float | None = Field(default=None, gt=0)
    floor_type: str | None = None
    door_count: int | None = Field(default=None, ge=0)
    window_count: int | None = Field(default=None, ge=0)


class ConfirmRoomsRequest(BaseModel):
    rooms: list[RoomEdit] = []
