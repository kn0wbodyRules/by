"""Google and GitHub sign-in (OAuth 2.0 authorization code flow).

Security notes, because this is the part that is easy to get subtly wrong:

* **CSRF** — every authorization request carries a signed, expiring `state`.
  The callback refuses anything it did not issue, so an attacker cannot feed a
  victim's browser a callback for an account the attacker controls.
* **Account linking** — an existing password account is only ever linked to a
  provider identity when the provider asserts the email is *verified*. Without
  that check, anyone who can set an unverified email at a provider could claim
  someone else's account here. GitHub in particular reports unverified
  addresses, so its primary+verified email is fetched explicitly.
* **Identity key** — accounts are matched on the provider's immutable subject
  id, not the email, since emails can be reassigned at the provider.

Behind OAUTH_MOCK_MODE (the default, and whenever a provider's credentials are
blank) the whole exchange is simulated locally, so the flow is testable before
any developer app exists. Never enable mock mode in production — it would let
anyone sign in as an arbitrary email.
"""

import hashlib
import hmac
import json
import secrets
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass

from app.config import get_settings
from app.core.exceptions import AuthError, ConfigError, DomainError

settings = get_settings()

STATE_TTL_SECONDS = 600


@dataclass(frozen=True)
class OAuthProfile:
    """Normalized identity, whichever provider it came from."""

    provider: str
    subject: str
    email: str
    name: str | None
    email_verified: bool


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    authorize_url: str
    token_url: str
    userinfo_url: str
    scope: str
    client_id: str
    client_secret: str


def _providers() -> dict[str, ProviderConfig]:
    return {
        "google": ProviderConfig(
            name="google",
            authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            userinfo_url="https://openidconnect.googleapis.com/v1/userinfo",
            scope="openid email profile",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
        ),
        "github": ProviderConfig(
            name="github",
            authorize_url="https://github.com/login/oauth/authorize",
            token_url="https://github.com/login/oauth/access_token",
            userinfo_url="https://api.github.com/user",
            scope="read:user user:email",
            client_id=settings.GITHUB_CLIENT_ID,
            client_secret=settings.GITHUB_CLIENT_SECRET,
        ),
    }


def get_provider(name: str) -> ProviderConfig:
    provider = _providers().get(name)
    if provider is None:
        raise DomainError(f"Unsupported sign-in provider: {name}")
    return provider


def is_mocked(provider: ProviderConfig) -> bool:
    """Mock unless this provider has real credentials and mock mode is off."""
    if settings.OAUTH_MOCK_MODE:
        return True
    return not (provider.client_id and provider.client_secret)


def redirect_uri(provider_name: str) -> str:
    return f"{settings.OAUTH_REDIRECT_BASE.rstrip('/')}/auth/oauth/{provider_name}/callback"


# --------------------------------------------------------------------------- state


def issue_state(provider_name: str) -> str:
    """`<provider>.<issued_at>.<nonce>.<hmac>` — self-contained, so no server-side
    session store is needed to validate it on the callback."""
    issued_at = str(int(time.time()))
    nonce = secrets.token_urlsafe(16)
    payload = f"{provider_name}.{issued_at}.{nonce}"
    return f"{payload}.{_sign(payload)}"


def verify_state(state: str, provider_name: str) -> None:
    try:
        provider_part, issued_at, nonce, signature = state.split(".")
    except ValueError:
        raise AuthError("Invalid sign-in state") from None

    payload = f"{provider_part}.{issued_at}.{nonce}"
    if not hmac.compare_digest(signature, _sign(payload)):
        raise AuthError("Invalid sign-in state")
    if provider_part != provider_name:
        raise AuthError("Sign-in state does not match this provider")
    if int(time.time()) - int(issued_at) > STATE_TTL_SECONDS:
        raise AuthError("Sign-in took too long — please try again")


def _sign(payload: str) -> str:
    return hmac.new(
        settings.JWT_SECRET_KEY.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()


# --------------------------------------------------------------------- authorize


def authorization_url(provider: ProviderConfig, state: str) -> str:
    params = {
        "client_id": provider.client_id,
        "redirect_uri": redirect_uri(provider.name),
        "scope": provider.scope,
        "state": state,
        "response_type": "code",
    }
    if provider.name == "google":
        # Ask for a fresh consent screen rather than silently reusing a session,
        # so switching Google accounts actually works.
        params["prompt"] = "select_account"
    return f"{provider.authorize_url}?{urllib.parse.urlencode(params)}"


# ------------------------------------------------------------------------ exchange


def exchange_code_for_profile(provider: ProviderConfig, code: str) -> OAuthProfile:
    if is_mocked(provider):
        return _mock_profile(provider, code)

    if settings.is_production and not (provider.client_id and provider.client_secret):
        raise ConfigError(f"{provider.name} sign-in is not configured")

    token = _post_form(
        provider.token_url,
        {
            "client_id": provider.client_id,
            "client_secret": provider.client_secret,
            "code": code,
            "redirect_uri": redirect_uri(provider.name),
            "grant_type": "authorization_code",
        },
    ).get("access_token")

    if not token:
        raise AuthError(f"{provider.name} did not return an access token")

    if provider.name == "google":
        info = _get_json(provider.userinfo_url, token)
        return OAuthProfile(
            provider="google",
            subject=str(info["sub"]),
            email=info.get("email", ""),
            name=info.get("name"),
            # Google returns this as a bool or the string "true" depending on path.
            email_verified=str(info.get("email_verified", "false")).lower() == "true",
        )

    info = _get_json(provider.userinfo_url, token)
    email, verified = _github_primary_email(token)
    return OAuthProfile(
        provider="github",
        subject=str(info["id"]),
        email=email or (info.get("email") or ""),
        name=info.get("name") or info.get("login"),
        email_verified=verified,
    )


def _github_primary_email(token: str) -> tuple[str | None, bool]:
    """GitHub's /user.email may be null or an unverified address, so the primary
    verified address is read from /user/emails instead."""
    try:
        emails = _get_json("https://api.github.com/user/emails", token)
    except Exception:  # noqa: BLE001 — treat an unreadable list as "unverified"
        return None, False
    if not isinstance(emails, list):
        return None, False
    for entry in emails:
        if entry.get("primary") and entry.get("verified"):
            return entry.get("email"), True
    for entry in emails:
        if entry.get("verified"):
            return entry.get("email"), True
    return None, False


def _post_form(url: str, data: dict[str, str]) -> dict:
    request = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(data).encode(),
        headers={"Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:  # noqa: S310 — fixed https hosts
        return json.loads(response.read().decode())


def _get_json(url: str, token: str) -> dict | list:
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "boq-automation-tool",
        },
    )
    with urllib.request.urlopen(request, timeout=15) as response:  # noqa: S310
        return json.loads(response.read().decode())


def _mock_profile(provider: ProviderConfig, code: str) -> OAuthProfile:
    """Deterministic stand-in so the flow is exercisable without a developer app.
    The code doubles as the local part of the email, which makes it easy to log in
    as different fake users during testing."""
    if settings.is_production:
        raise ConfigError(
            f"{provider.name} sign-in has no credentials configured — refusing to "
            "use mock sign-in in production"
        )
    handle = "".join(ch for ch in code if ch.isalnum())[:24] or "demo"
    return OAuthProfile(
        provider=provider.name,
        subject=f"mock-{provider.name}-{handle}",
        email=f"{handle}@{provider.name}.mock",
        name=f"{handle.capitalize()} ({provider.name} mock)",
        email_verified=True,
    )
