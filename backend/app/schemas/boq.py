from datetime import datetime

from pydantic import BaseModel

from app.models.enums import CorrectionConfidence, RoomSource, RoomType
from app.schemas.constraints import MaterialOverride
from app.schemas.room import Dimensions


class MaterialLine(BaseModel):
    material_name: str
    theoretical_quantity: float
    correction_factor: float
    correction_confidence: CorrectionConfidence
    quantity: float
    unit: str
    rate_per_unit: float
    total_cost: float


class BOQRoomOut(BaseModel):
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
    materials: list[MaterialLine]
    room_total_cost: float


class BOQConstraints(BaseModel):
    budget_cap: float | None
    material_overrides: list[MaterialOverride]


class BOQResponse(BaseModel):
    project_name: str
    location: str
    generated_at: datetime
    constraints: BOQConstraints
    rooms: list[BOQRoomOut]
    total_cost: float
    currency: str
