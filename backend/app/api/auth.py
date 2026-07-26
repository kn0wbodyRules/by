import secrets
from urllib.parse import quote

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.config import get_settings
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
    login_with_oauth,
    register_user,
    resend_otp,
    verify_otp,
)
from app.services.oauth_service import (
    authorization_url,
    exchange_code_for_profile,
    get_provider,
    is_mocked,
    issue_state,
    redirect_uri,
    verify_state,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/oauth/{provider_name}/start")
def oauth_start(provider_name: str):
    """Send the browser to the provider's consent screen.

    In mock mode there is no provider to visit, so this short-circuits straight
    to our own callback with a fake code — the rest of the flow is identical,
    which is what makes it testable without a developer app.
    """
    provider = get_provider(provider_name)
    state = issue_state(provider_name)

    if is_mocked(provider):
        code = f"mockuser{secrets.token_hex(3)}"
        return RedirectResponse(
            url=f"{redirect_uri(provider_name)}?code={code}&state={state}",
            status_code=302,
        )

    return RedirectResponse(url=authorization_url(provider, state), status_code=302)


@router.get("/oauth/{provider_name}/callback")
def oauth_callback(
    provider_name: str,
    state: str,
    code: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    settings = get_settings()
    provider = get_provider(provider_name)

    # The user can decline consent; that's a normal outcome, not a failure.
    if error or not code:
        return RedirectResponse(
            url=f"{settings.OAUTH_SUCCESS_REDIRECT}?error={quote(error or 'cancelled')}",
            status_code=302,
        )

    verify_state(state, provider_name)
    profile = exchange_code_for_profile(provider, code)
    user = login_with_oauth(db, profile)
    token = create_access_token(subject=user.id)

    # The token rides back in the fragment, not the query string: fragments are
    # never sent to servers and stay out of referrer headers and access logs.
    return RedirectResponse(
        url=f"{settings.OAUTH_SUCCESS_REDIRECT}#access_token={token}", status_code=302
    )


@router.post("/register", response_model=RegisterResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    user, email_sent = register_user(db, payload.email, payload.password, payload.name)
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
