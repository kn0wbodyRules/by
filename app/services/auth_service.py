from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.exceptions import AuthError, DomainError
from app.core.security import (
    generate_otp_code,
    hash_otp_code,
    hash_password,
    verify_otp_code,
    verify_password,
)
from app.models.user import User
from app.services.email_service import send_otp_email

settings = get_settings()


def _issue_otp(db: Session, user: User) -> None:
    otp_code = generate_otp_code()
    user.otp_code_hash = hash_otp_code(otp_code)
    user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
    user.otp_attempts = 0
    db.add(user)
    db.commit()
    send_otp_email(user.email, otp_code)


def register_user(db: Session, email: str, password: str) -> User:
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise DomainError("An account with this email already exists")

    user = User(email=email, hashed_password=hash_password(password), is_verified=False)
    db.add(user)
    db.commit()
    db.refresh(user)

    _issue_otp(db, user)
    return user


def verify_otp(db: Session, email: str, otp_code: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.otp_code_hash or not user.otp_expires_at:
        raise AuthError("No pending verification for this email")

    if datetime.now(timezone.utc) > user.otp_expires_at:
        raise AuthError("Verification code has expired")

    if user.otp_attempts >= settings.OTP_MAX_ATTEMPTS:
        raise AuthError("Too many incorrect attempts — please register again")

    if not verify_otp_code(otp_code, user.otp_code_hash):
        user.otp_attempts += 1
        db.add(user)
        db.commit()
        raise AuthError("Incorrect verification code")

    user.is_verified = True
    user.otp_code_hash = None
    user.otp_expires_at = None
    user.otp_attempts = 0
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise AuthError("Incorrect email or password")
    if not user.is_verified:
        raise AuthError("Account not verified — check your email for a verification code")
    return user
