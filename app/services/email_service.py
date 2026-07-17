"""OTP email delivery. Real SMTP send when SMTP_HOST is configured; in development
with no SMTP config, logs the OTP to the console instead so auth stays testable
before real credentials exist. Blank SMTP config under ENV=production raises instead
of silently no-op'ing, so a misconfigured deploy fails loudly, not quietly.
"""

import logging
import smtplib
from email.message import EmailMessage

from app.config import get_settings
from app.core.exceptions import ConfigError

logger = logging.getLogger("boq.email")
settings = get_settings()


def send_otp_email(to_email: str, otp_code: str) -> None:
    if not settings.SMTP_HOST:
        if settings.is_production:
            raise ConfigError("SMTP_HOST is not configured — cannot send OTP email in production")
        logger.warning("DEV MODE (no SMTP configured) — OTP for %s is: %s", to_email, otp_code)
        return

    message = EmailMessage()
    message["Subject"] = "Your BOQ Automation Tool verification code"
    message["From"] = settings.SMTP_FROM
    message["To"] = to_email
    message.set_content(
        f"Your verification code is: {otp_code}\n\n"
        f"This code expires in {settings.OTP_EXPIRY_MINUTES} minutes."
    )

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        if settings.SMTP_USER:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(message)
