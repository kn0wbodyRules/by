from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import AuthError, NotFoundError
from app.core.security import decode_access_token
from app.database import get_db
from app.models.job import Job
from app.models.user import User

_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise AuthError("Missing bearer token")

    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise AuthError("Invalid token payload")

    user = db.get(User, user_id)
    if not user:
        raise AuthError("User no longer exists")
    return user


def get_job_or_404(job_id: str, db: Session, current_user: User) -> Job:
    job = db.get(Job, job_id)
    if not job or job.user_id != current_user.id:
        raise NotFoundError(f"Job {job_id} not found")
    return job


__all__ = ["get_db", "get_current_user", "get_job_or_404"]
