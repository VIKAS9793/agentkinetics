from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Protocol


class ArtifactStore(Protocol):
    def write_bytes(self, relative_path: str, payload: bytes) -> str:
        ...


class LocalArtifactStore:
    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    def write_bytes(self, relative_path: str, payload: bytes) -> str:
        target = self._root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        return hashlib.sha256(payload).hexdigest()
