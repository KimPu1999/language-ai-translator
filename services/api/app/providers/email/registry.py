from app.core.config import Settings, get_settings
from app.providers.email.base import EmailProvider
from app.providers.email.smtp import (
    DevelopmentMailboxProvider,
    SMTPEmailProvider,
    UnavailableEmailProvider,
)


def get_email_provider(settings: Settings | None = None) -> EmailProvider:
    settings = settings or get_settings()
    if settings.auth_smtp_host:
        return SMTPEmailProvider(settings)
    if settings.auth_dev_mailbox_dir:
        return DevelopmentMailboxProvider(settings.auth_dev_mailbox_dir)
    return UnavailableEmailProvider()
