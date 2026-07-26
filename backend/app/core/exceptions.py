class DomainError(Exception):
    """Base class for expected, user-facing domain errors (mapped to clean HTTP
    responses in main.py) as opposed to unexpected bugs, which should surface as 500s."""

    status_code = 400

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class InvalidStateTransitionError(DomainError):
    status_code = 409


class NotFoundError(DomainError):
    status_code = 404


class AuthError(DomainError):
    status_code = 401


class ValidationDomainError(DomainError):
    status_code = 422


class ConfigError(DomainError):
    """Raised at startup/call time when required config is missing (e.g. blank SMTP
    in production) — fails loudly instead of silently no-op'ing."""

    status_code = 500


class EmailDeliveryError(DomainError):
    """Raised when SMTP is configured but the send itself fails (host unreachable,
    auth rejected, port blocked). Distinct from ConfigError so callers can decide
    whether a failed send should abort the request or just be reported — registration
    treats it as non-fatal so the account isn't stranded."""

    status_code = 502
