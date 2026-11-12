from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import BinaryIO


@dataclass(frozen=True)
class DocumentBlock:
    text: str
    kind: str
    page: int | None = None
    location: str | None = None


@dataclass(frozen=True)
class ExtractedDocument:
    format: str
    blocks: tuple[DocumentBlock, ...]
    text: str
    pages: int
    ocr_pages: tuple[int, ...] = ()


class DocumentExtractionError(Exception):
    def __init__(self, code: str, message: str, *, status_code: int = 422) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class DocumentExtractor(ABC):
    format: str

    @abstractmethod
    def extract(self, stream: BinaryIO, *, source_language: str | None = None) -> ExtractedDocument:
        raise NotImplementedError
