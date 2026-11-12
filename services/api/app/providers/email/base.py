from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class EmailMessage:
    recipient: str
    subject: str
    body: str


class EmailDeliveryError(Exception):
    """Raised when an action email was not accepted by the configured provider."""


class EmailProvider(ABC):
    name = "abstract"

    @abstractmethod
    async def send(self, message: EmailMessage) -> None:
        raise NotImplementedError
