import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings
from app.core.exceptions import AuthError

settings = get_settings()

# pbkdf2_sha256, not bcrypt: passlib 1.7.4 (unmaintained) fails its own backend
# self-test against bcrypt>=4.1's stricter 72-byte handling. pbkdf2_sha256 is pure
# Python, has no such incompatibility, and is a drop-in via the same passlib API.
_pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise AuthError("Invalid or expired token") from exc


def generate_otp_code() -> str:
    """Cryptographically random numeric OTP of settings.OTP_LENGTH digits."""
    return "".join(secrets.choice("0123456789") for _ in range(settings.OTP_LENGTH))


def hash_otp_code(code: str) -> str:
    return _pwd_context.hash(code)


def verify_otp_code(plain_code: str, hashed_code: str) -> bool:
    return _pwd_context.verify(plain_code, hashed_code)
