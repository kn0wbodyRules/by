import pytest

from app.core.exceptions import AuthError, DomainError
from app.services import auth_service


@pytest.fixture()
def captured_otp(monkeypatch):
    """Intercepts the OTP that would be emailed, without needing real SMTP."""
    box: dict[str, str] = {}

    def _fake_send(to_email: str, otp_code: str) -> None:
        box["email"] = to_email
        box["otp_code"] = otp_code

    monkeypatch.setattr(auth_service, "send_otp_email", _fake_send)
    return box


def test_register_creates_unverified_user_and_sends_otp(db, captured_otp):
    user = auth_service.register_user(db, "alice@example.com", "password123")
    assert user.is_verified is False
    assert user.otp_code_hash is not None
    assert captured_otp["email"] == "alice@example.com"
    assert len(captured_otp["otp_code"]) == 6


def test_register_duplicate_email_rejected(db, captured_otp):
    auth_service.register_user(db, "alice@example.com", "password123")
    with pytest.raises(DomainError):
        auth_service.register_user(db, "alice@example.com", "password456")


def test_verify_otp_success_marks_verified(db, captured_otp):
    auth_service.register_user(db, "alice@example.com", "password123")
    otp_code = captured_otp["otp_code"]

    user = auth_service.verify_otp(db, "alice@example.com", otp_code)
    assert user.is_verified is True
    assert user.otp_code_hash is None


def test_verify_otp_wrong_code_rejected(db, captured_otp):
    auth_service.register_user(db, "alice@example.com", "password123")
    with pytest.raises(AuthError):
        auth_service.verify_otp(db, "alice@example.com", "000000")


def test_verify_otp_exceeding_max_attempts_locks_out(db, captured_otp):
    auth_service.register_user(db, "alice@example.com", "password123")
    for _ in range(5):
        with pytest.raises(AuthError):
            auth_service.verify_otp(db, "alice@example.com", "000000")
    # the correct code should now also be rejected — attempts exhausted
    with pytest.raises(AuthError):
        auth_service.verify_otp(db, "alice@example.com", captured_otp["otp_code"])


def test_authenticate_requires_verification(db, captured_otp):
    auth_service.register_user(db, "alice@example.com", "password123")
    with pytest.raises(AuthError):
        auth_service.authenticate_user(db, "alice@example.com", "password123")


def test_authenticate_success_after_verification(db, captured_otp):
    auth_service.register_user(db, "alice@example.com", "password123")
    auth_service.verify_otp(db, "alice@example.com", captured_otp["otp_code"])

    user = auth_service.authenticate_user(db, "alice@example.com", "password123")
    assert user.email == "alice@example.com"


def test_authenticate_wrong_password_rejected(db, captured_otp):
    auth_service.register_user(db, "alice@example.com", "password123")
    auth_service.verify_otp(db, "alice@example.com", captured_otp["otp_code"])
    with pytest.raises(AuthError):
        auth_service.authenticate_user(db, "alice@example.com", "wrongpassword")
