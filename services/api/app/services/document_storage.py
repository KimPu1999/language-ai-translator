from __future__ import annotations

import os
import secrets
from pathlib import Path


class PrivateDocumentStorage:
    def __init__(self, root: str) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)

    def key(self, document_format: str) -> str:
        return f"{secrets.token_hex(24)}.{document_format}"

    def write(self, key: str, data: bytes) -> Path:
        target = self._path(key)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        descriptor = os.open(target, flags, 0o600)
        try:
            with os.fdopen(descriptor, "wb") as output:
                output.write(data)
        except Exception:
            try:
                target.unlink(missing_ok=True)
            finally:
                raise
        return target

    def read(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    def _path(self, key: str) -> Path:
        candidate = (self.root / key).resolve()
        if candidate.parent != self.root or candidate.name != key:
            raise ValueError("invalid document storage key")
        return candidate
