"""OAuth sign-in: state signing, account linking rules, and the mock flow.

The linking tests are the important ones — they encode who is allowed to take
over an existing account, which is where OAuth integrations usually go wrong.
"""

import time

import pytest

from app.core.exceptions import AuthError, DomainError
from app.core.security import hash_password
from app.models.user import User
from app.services import oauth_service
from app.services.auth_service import authenticate_user, login_with_oauth
from app.services.oauth_service import OAuthProfile


def _profile(**overrides) -> OAuthProfile:
    base = dict(
        provider="google",
        subject="google-sub-1",
        email="alice@example.com",
        name="Alice",
        email_verified=True,
    )
    base.update(overrides)
    return OAuthProfile(**base)


# ----------------------------------------------------------------- state / CSRF


def test_state_roundtrip_is_accepted():
    state = oauth_service.issue_state("google")
    oauth_service.verify_state(state, "google")  # must not raise


def test_tampered_state_is_rejected():
    state = oauth_service.issue_state("google")
    payload, _, signature = state.rpartition(".")
    forged = f"{payload}.{'0' * len(signature)}"
    with pytest.raises(AuthError):
        oauth_service.verify_state(forged, "google")


def test_state_from_another_provider_is_rejected():
    state = oauth_service.issue_state("github")
    with pytest.raises(AuthError):
        oauth_service.verify_state(state, "google")


def test_expired_state_is_rejected(monkeypatch):
    state = oauth_service.issue_state("google")
    # Capture the real clock before patching — reading time.time() inside the
    # replacement would call the replacement itself and recurse forever.
    future = time.time() + oauth_service.STATE_TTL_SECONDS + 5
    monkeypatch.setattr(oauth_service.time, "time", lambda: future)
    with pytest.raises(AuthError):
        oauth_service.verify_state(state, "google")


def test_unknown_provider_rejected():
    with pytest.raises(DomainError):
        oauth_service.get_provider("myspace")


# -------------------------------------------------------------- account linking


def test_first_oauth_login_creates_verified_passwordless_account(db):
    user = login_with_oauth(db, _profile())

    assert user.email == "alice@example.com"
    assert user.name == "Alice"
    assert user.is_verified is True
    # No password: this account can only ever come back through its provider.
    assert user.hashed_password is None
    assert (user.oauth_provider, user.oauth_subject) == ("google", "google-sub-1")


def test_returning_oauth_user_is_matched_on_subject_not_email(db):
    first = login_with_oauth(db, _profile())
    # Provider emails can be reassigned; the subject is what identifies the account.
    second = login_with_oauth(db, _profile(email="alice.new@example.com"))

    assert first.id == second.id
    assert db.query(User).count() == 1


def test_verified_email_links_to_existing_password_account(db):
    existing = User(
        email="alice@example.com", hashed_password=hash_password("password123"), is_verified=True
    )
    db.add(existing)
    db.commit()

    linked = login_with_oauth(db, _profile(email_verified=True))

    assert linked.id == existing.id
    assert linked.oauth_provider == "google"
    # Linking must not destroy the existing password login.
    assert linked.hashed_password is not None
    assert db.query(User).count() == 1


def test_unverified_email_cannot_hijack_existing_account(db):
    """The core protection: without this check, anyone who sets an unverified
    address at a provider could sign in as an existing user of this app."""
    existing = User(
        email="alice@example.com", hashed_password=hash_password("password123"), is_verified=True
    )
    db.add(existing)
    db.commit()

    with pytest.raises(AuthError):
        login_with_oauth(db, _profile(email_verified=False))

    db.rollback()
    untouched = db.query(User).filter(User.email == "alice@example.com").one()
    assert untouched.oauth_provider is None


def test_oauth_account_rejects_password_login_with_clear_message(db):
    login_with_oauth(db, _profile())

    with pytest.raises(AuthError) as excinfo:
        authenticate_user(db, "alice@example.com", "anything")
    assert "google" in str(excinfo.value).lower()


def test_profile_without_email_cannot_create_account(db):
    with pytest.raises(AuthError):
        login_with_oauth(db, _profile(email=""))


# ------------------------------------------------------------------- mock mode


def test_mock_profile_is_used_when_credentials_are_blank():
    provider = oauth_service.get_provider("github")
    assert oauth_service.is_mocked(provider) is True

    profile = oauth_service.exchange_code_for_profile(provider, "mockuserabc")
    assert profile.provider == "github"
    assert profile.email.endswith("@github.mock")
    assert profile.email_verified is True
