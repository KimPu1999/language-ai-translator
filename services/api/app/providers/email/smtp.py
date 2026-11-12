from __future__ import annotations

import asyncio
import os
import smtplib
from email.message import EmailMessage as SMTPMessage
from pathlib import Path

from app.core.config import Settings
from app.providers.email.base import EmailDeliveryError, EmailMessage, EmailProvider


class SMTPEmailProvider(EmailProvider):
    name = "smtp"

    def __init__(self, settings: Settings) -> None:
        if not all(
            (
                settings.auth_smtp_host,
                settings.auth_smtp_username,
                settings.auth_smtp_password,
                settings.auth_smtp_from,
            )
        ):
            raise ValueError("SMTP email configuration is incomplete")
        self._settings = settings

    async def send(self, message: EmailMessage) -> None:
        try:
            await asyncio.to_thread(self._send_blocking, message)
        except (OSError, smtplib.SMTPException) as exc:
            raise EmailDeliveryError("Email delivery failed") from exc

    def _send_blocking(self, message: EmailMessage) -> None:
        smtp_message = SMTPMessage()
        smtp_message["From"] = self._settings.auth_smtp_from
        smtp_message["To"] = message.recipient
        smtp_message["Subject"] = message.subject
        smtp_message.set_content(message.body)
        password = self._settings.auth_smtp_password
        with smtplib.SMTP(
            self._settings.auth_smtp_host,
            self._settings.auth_smtp_port,
            timeout=10,
        ) as client:
            if self._settings.auth_smtp_starttls:
                client.starttls()
            client.login(self._settings.auth_smtp_username, password.get_secret_value())
            client.send_message(smtp_message)


class DevelopmentMailboxProvider(EmailProvider):
    """Writes test mail to a private development-only mailbox directory.

    This is intentionally not an HTTP endpoint and does not claim SMTP delivery.
    """

    name = "development-mailbox"

    def __init__(self, directory: str) -> None:
        self._directory = Path(directory).resolve()
        self._directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self._directory, 0o700)

    async def send(self, message: EmailMessage) -> None:
        safe_name = f"{os.urandom(16).hex()}.eml"
        target = self._directory / safe_name
        target.write_text(
            f"To: {message.recipient}\nSubject: {message.subject}\n\n{message.body}\n",
            encoding="utf-8",
        )
        os.chmod(target, 0o600)


class UnavailableEmailProvider(EmailProvider):
    name = "unavailable"

    async def send(self, message: EmailMessage) -> None:
        del message
        raise EmailDeliveryError("Email delivery is not configured")
