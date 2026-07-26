import mimetypes
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_job_or_404
from app.core.exceptions import DomainError
from app.models.enums import JobStatus
from app.models.room import Room
from app.models.user import User
from app.schemas.room import ConfirmRoomsRequest, DetectRoomsResponse, ManualRoomsRequest, RoomOut
from app.services.gemini_vision import call_gemini_vision
from app.services.job_state_machine import require_status, transition
from app.services.room_normalizer import (
    apply_room_edit,
    normalize_gemini_rooms,
    normalize_manual_room,
    room_create_to_model,
    room_to_out,
)

router = APIRouter(tags=["rooms"])


@router.get("/rooms/{job_id}", response_model=list[RoomOut])
def list_rooms(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Read a job's rooms at any point in the flow.

    Rooms were previously only observable as the return value of the endpoints
    that create or edit them, and GET /boq requires the job to be calculated — so
    a client that reloaded mid-flow had no way to recover what it had already
    entered. Deliberately not status-gated: reading is safe in every state.
    """
    get_job_or_404(job_id, db, current_user)
    rooms = db.query(Room).filter(Room.job_id == job_id).all()
    return [room_to_out(r) for r in rooms]


@router.post("/manual-rooms/{job_id}", response_model=list[RoomOut])
def create_manual_rooms(
    job_id: str,
    payload: ManualRoomsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = get_job_or_404(job_id, db, current_user)
    require_status(job, JobStatus.UPLOADED)

    if not payload.rooms:
        raise DomainError("At least one room is required")

    rooms = []
    for room_input in payload.rooms:
        room_create = normalize_manual_room(room_input)
        room = room_create_to_model(room_create, job_id)
        db.add(room)
        rooms.append(room)

    transition(db, job, JobStatus.ROOMS_MANUAL)
    for room in rooms:
        db.refresh(room)

    return [room_to_out(r) for r in rooms]


@router.post("/detect-rooms/{job_id}", response_model=DetectRoomsResponse)
def detect_rooms(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = get_job_or_404(job_id, db, current_user)
    require_status(job, JobStatus.UPLOADED)

    if not job.uploaded_file_path:
        raise DomainError("No uploaded floor plan file for this job")

    path = Path(job.uploaded_file_path)
    image_bytes = path.read_bytes()
    mime_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"

    raw_rows = call_gemini_vision(image_bytes, mime_type)
    accepted, rejected = normalize_gemini_rooms(raw_rows)

    if not accepted:
        raise DomainError("No valid rooms could be detected from the uploaded floor plan")

    rooms = []
    for room_create in accepted:
        room = room_create_to_model(room_create, job_id)
        db.add(room)
        rooms.append(room)

    transition(db, job, JobStatus.ROOMS_DETECTED)
    for room in rooms:
        db.refresh(room)

    return DetectRoomsResponse(
        rooms=[room_to_out(r) for r in rooms],
        rejected_count=len(rejected),
        rejections=[r.model_dump() for r in rejected],
    )


@router.patch("/confirm-rooms/{job_id}", response_model=list[RoomOut])
def confirm_rooms(
    job_id: str,
    payload: ConfirmRoomsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = get_job_or_404(job_id, db, current_user)
    require_status(job, JobStatus.ROOMS_DETECTED, JobStatus.ROOMS_MANUAL)

    rooms = db.query(Room).filter(Room.job_id == job_id).all()
    if not rooms:
        raise DomainError("No rooms to confirm")
    rooms_by_id = {r.id: r for r in rooms}

    for edit in payload.rooms:
        room = rooms_by_id.get(edit.room_id)
        if room is None:
            raise DomainError(f"Room {edit.room_id} does not belong to this job")
        apply_room_edit(room, edit)

    for room in rooms:
        room.confirmed = True
        db.add(room)

    transition(db, job, JobStatus.ROOMS_CONFIRMED)
    for room in rooms:
        db.refresh(room)

    return [room_to_out(r) for r in rooms]
