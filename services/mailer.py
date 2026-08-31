from __future__ import annotations

import smtplib
from email.message import EmailMessage

from config.settings import get_settings


def send_password_reset_email(recipient: str, token: str) -> bool:
    """Send a reset code through configured Gmail SMTP; never log credentials or tokens."""
    settings = get_settings()
    if settings.email_mode != "smtp" or not all((settings.smtp_username, settings.smtp_password, settings.smtp_sender)):
        return False
    message = EmailMessage()
    message["Subject"] = "Password reset code"
    message["From"] = settings.smtp_sender
    message["To"] = recipient
    message.set_content(
        f"Your password reset code is: {token}\n\nIt expires in 15 minutes. If you did not request it, ignore this email."
    )
    with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
        smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)
    return True
