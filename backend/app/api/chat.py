from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_job_or_404
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import handle_chat_message

router = APIRouter(tags=["chat"])


@router.post("/chat/{job_id}", response_model=ChatResponse)
def chat(
    job_id: str,
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = get_job_or_404(job_id, db, current_user)
    return handle_chat_message(job, payload.message)
