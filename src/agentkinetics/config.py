from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


DEFAULT_DATABASE_FILENAME = "agentkinetics.sqlite3"
DEFAULT_ARTIFACTS_DIRECTORY = "artifacts"
DEFAULT_TENANT_NAME = "local-default"


@dataclass(frozen=True)
class AppConfig:
    database_path: Path = Path("data") / DEFAULT_DATABASE_FILENAME
    artifacts_dir: Path = Path("data") / DEFAULT_ARTIFACTS_DIRECTORY
    default_tenant_name: str = DEFAULT_TENANT_NAME
    session_ttl_hours: int = 12
