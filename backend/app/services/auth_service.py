from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.exceptions import AuthError, DomainError, EmailDeliveryError
from app.core.security import (
    generate_otp_code,
    hash_otp_code,
    hash_password,
    verify_otp_code,
    verify_password,
)
from app.models.user import User
from app.services.email_service import send_otp_email
from app.services.oauth_service import OAuthProfile

settings = get_settings()


def _issue_otp(db: Session, user: User) -> bool:
    """Generate, persist and send a fresh OTP. Returns whether delivery succeeded.

    Delivery failure is reported rather than raised: the account row is already
    committed by this point, so aborting here would strand the user in an
    unrecoverable state (cannot re-register — email taken; cannot log in — unverified;
    cannot get a code — send failed). Callers surface `email_sent` instead, and the
    user recovers via resend_otp once mail delivery is working.
    """
    otp_code = generate_otp_code()
    user.otp_code_hash = hash_otp_code(otp_code)
    user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
    user.otp_attempts = 0
    db.add(user)
    db.commit()

    try:
        send_otp_email(user.email, otp_code)
    except EmailDeliveryError:
        return False
    return True


def register_user(
    db: Session, email: str, password: str, name: str | None = None
) -> tuple[User, bool]:
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise DomainError("An account with this email already exists")

    user = User(
        email=email,
        name=(name or None),
        hashed_password=hash_password(password),
        is_verified=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    email_sent = _issue_otp(db, user)
    return user, email_sent


def login_with_oauth(db: Session, profile: OAuthProfile) -> User:
    """Resolve a provider identity to a local account, creating or linking as needed.

    Matching is on the provider's immutable subject id. Falling back to email is
    only safe when the provider says the address is verified — otherwise someone
    who sets an unverified address at a provider could take over an existing
    password account here.
    """
    user = (
        db.query(User)
        .filter(
            User.oauth_provider == profile.provider,
            User.oauth_subject == profile.subject,
        )
        .first()
    )

    if user is None and profile.email:
        by_email = db.query(User).filter(User.email == profile.email).first()
        if by_email is not None:
            if not profile.email_verified:
                raise AuthError(
                    f"An account already uses {profile.email}. Sign in with your "
                    f"password, or verify that address with {profile.provider} first."
                )
            by_email.oauth_provider = profile.provider
            by_email.oauth_subject = profile.subject
            user = by_email

    if user is None:
        if not profile.email:
            raise AuthError(
                f"{profile.provider} did not share a verified email address, so an "
                "account cannot be created."
            )
        user = User(
            email=profile.email,
            name=profile.name,
            # No password: this account can only ever sign in via its provider.
            hashed_password=None,
            oauth_provider=profile.provider,
            oauth_subject=profile.subject,
        )
        db.add(user)

    # The provider already proved control of the mailbox, so no OTP round-trip.
    user.is_verified = True
    if profile.name and not user.name:
        user.name = profile.name

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def resend_otp(db: Session, email: str) -> bool:
    """Issue a fresh OTP for an existing unverified account.

    Recovery path for the case where the original send failed (blocked SMTP port,
    transient outage) or the code expired. Deliberately does not reveal whether the
    address is registered — the response is identical either way, so this cannot be
    used to enumerate accounts.
    """
    user = db.query(User).filter(User.email == email).first()
    if not user or user.is_verified:
        return True
    return _issue_otp(db, user)


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

    # An OAuth-only account has no password hash to compare against. Say so
    # explicitly rather than letting verify_password choke on None — the user
    # needs to know which button to press.
    if user is not None and user.hashed_password is None:
        provider = user.oauth_provider or "your sign-in provider"
        raise AuthError(f"This account signs in with {provider}. Use that button instead.")

    if not user or not verify_password(password, user.hashed_password):
        raise AuthError("Incorrect email or password")
    if not user.is_verified:
        raise AuthError("Account not verified — check your email for a verification code")
    return user
