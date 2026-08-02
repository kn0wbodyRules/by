"""Stage 1-2/3 — forces rooms into the identical schema whether they arrive via
Gemini Vision or manual entry, and applies Confirm-screen edits before persisting.
"""

from pydantic import BaseModel

from app.models.enums import RoomSource, RoomType
from app.models.room import Room
from app.schemas.room import Dimensions, ManualRoomInput, RoomEdit, RoomOut
from app.services.room_classifier import classify_room_type_escalated, compute_aspect_ratio


class RoomCreate(BaseModel):
    room_name: str
    room_name_raw: str
    room_type: RoomType
    area_sqft: float
    length_ft: float
    width_ft: float
    ceiling_height_ft: float
    wall_thickness_ft: float
    floor_type: str
    door_count: int
    window_count: int
    source: RoomSource
    exception_text: str | None = None


class RoomRejection(BaseModel):
    reason: str
    raw_row: dict


# Gemini Vision analyzes a 2D photo and cannot reliably see ceiling height or wall
# thickness — these are only in the contract at all because of the v3 amendment.
# Defaulting to common Indian residential construction values lets Gemini-detected
# rooms flow through; the Figma Confirm screen's editable fields are exactly where
# the user corrects them before calculation.
DEFAULT_CEILING_HEIGHT_FT = 9.0
DEFAULT_WALL_THICKNESS_FT = 0.75


def _build_room_create(
    room_name_raw: str,
    length_ft: float,
    width_ft: float,
    ceiling_height_ft: float,
    wall_thickness_ft: float,
    floor_type: str,
    door_count: int,
    window_count: int,
    source: RoomSource,
    exception_text: str | None = None,
) -> RoomCreate:
    area_sqft = length_ft * width_ft
    aspect_ratio = compute_aspect_ratio(length_ft, width_ft)
    room_type = classify_room_type_escalated(
        room_name_raw,
        area_sqft=area_sqft,
        aspect_ratio=aspect_ratio,
        door_count=door_count,
        window_count=window_count,
    )
    return RoomCreate(
        room_name=room_name_raw,
        room_name_raw=room_name_raw,
        room_type=room_type,
        area_sqft=area_sqft,
        length_ft=length_ft,
        width_ft=width_ft,
        ceiling_height_ft=ceiling_height_ft,
        wall_thickness_ft=wall_thickness_ft,
        floor_type=floor_type,
        door_count=door_count,
        window_count=window_count,
        source=source,
        exception_text=exception_text,
    )


def normalize_manual_room(payload: ManualRoomInput) -> RoomCreate:
    return _build_room_create(
        room_name_raw=payload.room_name,
        length_ft=payload.length_ft,
        width_ft=payload.width_ft,
        ceiling_height_ft=payload.ceiling_height_ft,
        wall_thickness_ft=payload.wall_thickness_ft,
        floor_type=payload.floor_type,
        door_count=payload.door_count,
        window_count=payload.window_count,
        source=RoomSource.MANUAL,
        exception_text=payload.exception_text,
    )


def normalize_gemini_rooms(raw_rows: list[dict]) -> tuple[list[RoomCreate], list[RoomRejection]]:
    """Gemini's output is untrusted JSON — coerce/validate defensively, collecting
    malformed rows as rejections (partial success) instead of crashing the request."""
    accepted: list[RoomCreate] = []
    rejected: list[RoomRejection] = []

    for row in raw_rows:
        try:
            room_name_raw = str(row["room_name"]).strip()
            if not room_name_raw:
                raise ValueError("room_name is empty")

            length_ft = float(row["length_ft"])
            width_ft = float(row["width_ft"])
            ceiling_height_ft = float(row.get("ceiling_height_ft") or DEFAULT_CEILING_HEIGHT_FT)
            wall_thickness_ft = float(row.get("wall_thickness_ft") or DEFAULT_WALL_THICKNESS_FT)
            if length_ft <= 0 or width_ft <= 0 or ceiling_height_ft <= 0 or wall_thickness_ft <= 0:
                raise ValueError("dimensions must be positive")

            floor_type = str(row.get("floor_type") or "")
            door_count = int(row.get("door_count") or 0)
            window_count = int(row.get("window_count") or 0)

            accepted.append(
                _build_room_create(
                    room_name_raw=room_name_raw,
                    length_ft=length_ft,
                    width_ft=width_ft,
                    ceiling_height_ft=ceiling_height_ft,
                    wall_thickness_ft=wall_thickness_ft,
                    floor_type=floor_type,
                    door_count=door_count,
                    window_count=window_count,
                    source=RoomSource.GEMINI_VISION,
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            rejected.append(RoomRejection(reason=str(exc), raw_row=row))

    return accepted, rejected


def room_create_to_model(room_create: RoomCreate, job_id: str) -> Room:
    return Room(
        job_id=job_id,
        room_name=room_create.room_name,
        room_name_raw=room_create.room_name_raw,
        room_type=room_create.room_type,
        area_sqft=room_create.area_sqft,
        length_ft=room_create.length_ft,
        width_ft=room_create.width_ft,
        ceiling_height_ft=room_create.ceiling_height_ft,
        wall_thickness_ft=room_create.wall_thickness_ft,
        floor_type=room_create.floor_type,
        door_count=room_create.door_count,
        window_count=room_create.window_count,
        source=room_create.source,
        confirmed=False,
        exception_text=room_create.exception_text,
    )


def apply_room_edit(room: Room, edit: RoomEdit) -> None:
    data = edit.model_dump(exclude={"room_id"}, exclude_none=True)
    for field, value in data.items():
        setattr(room, field, value)
    if "length_ft" in data or "width_ft" in data:
        room.area_sqft = float(room.length_ft) * float(room.width_ft)


def room_to_out(room: Room) -> RoomOut:
    return RoomOut(
        room_id=room.id,
        room_name=room.room_name,
        room_name_raw=room.room_name_raw,
        room_type=room.room_type,
        area_sqft=float(room.area_sqft),
        dimensions=Dimensions(
            length_ft=float(room.length_ft),
            width_ft=float(room.width_ft),
            ceiling_height_ft=float(room.ceiling_height_ft),
            wall_thickness_ft=float(room.wall_thickness_ft),
        ),
        floor_type=room.floor_type,
        door_count=room.door_count,
        window_count=room.window_count,
        source=room.source,
        confirmed=room.confirmed,
        exception_text=room.exception_text,
        exception_applied=room.exception_applied,
    )
