from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    ResendOTPRequest,
    ResendOTPResponse,
    TokenResponse,
    UserOut,
    VerifyOTPRequest,
)
from app.services.auth_service import (
    authenticate_user,
    register_user,
    resend_otp,
    verify_otp,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    user, email_sent = register_user(db, payload.email, payload.password)
    message = (
        "Registration successful. Check your email for a verification code."
        if email_sent
        else "Account created, but the verification email could not be sent. "
        "Use /auth/resend-otp once mail delivery is working."
    )
    return RegisterResponse(
        user_id=user.id, email=user.email, email_sent=email_sent, message=message
    )


@router.post("/resend-otp", response_model=ResendOTPResponse)
def resend_otp_endpoint(payload: ResendOTPRequest, db: Session = Depends(get_db)):
    email_sent = resend_otp(db, payload.email)
    return ResendOTPResponse(email_sent=email_sent)


@router.post("/verify-otp", response_model=TokenResponse)
def verify_otp_endpoint(payload: VerifyOTPRequest, db: Session = Depends(get_db)):
    user = verify_otp(db, payload.email, payload.otp_code)
    token = create_access_token(subject=user.id)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload.email, payload.password)
    token = create_access_token(subject=user.id)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
