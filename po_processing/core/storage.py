"""
Storage abstraction -- single source of truth for data paths and file IO.

All persistent data (agent output, ALF output, investigation output, the rule
base, the rules book, learning sessions, and the exemplary input cases) lives
under a configurable root:

  * If ``VOLUME_BASE`` is set (e.g. a Databricks Volume mount such as
    ``/Volumes/<catalog>/<schema>/<volume>``), that directory is the data root.
  * Otherwise we fall back to the package-local layout (``<package>/data`` and
    ``<package>/exemplary_data``) so local development works with no config.

Databricks Volumes are POSIX-mounted, so ``pathlib`` / ``open()`` work directly.
All IO is funneled through the helpers below so a future non-POSIX backend
(e.g. ``dbutils.fs`` or S3) only requires changing this one module.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Roots
# ---------------------------------------------------------------------------

# storage.py lives at <package>/core/storage.py -> package dir is two levels up.
PACKAGE_DIR = Path(__file__).resolve().parent.parent
# Repo root (used for .env resolution in local dev).
PROJECT_ROOT = PACKAGE_DIR.parent

_VOLUME_BASE = os.getenv("VOLUME_BASE")
DATA_ROOT = Path(_VOLUME_BASE) if _VOLUME_BASE else PACKAGE_DIR

# ---------------------------------------------------------------------------
# .env loading (local-dev convenience; on Databricks env comes from App config)
# ---------------------------------------------------------------------------

try:
    from dotenv import load_dotenv

    _env_file = PROJECT_ROOT / ".env"
    if _env_file.exists():
        load_dotenv(_env_file)
    else:
        load_dotenv()
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Derived data paths (the single source of truth for the whole package)
# ---------------------------------------------------------------------------

DATA_DIR = DATA_ROOT / "data"
EXEMPLARY_DIR = DATA_ROOT / "exemplary_data"

AGENTIC_FLOW_OUT = DATA_DIR / "agent_output"
ALF_OUT_DIR = DATA_DIR / "alf_output"
INVESTIGATION_OUTPUT_DIR = DATA_DIR / "investigation_output"
SESSIONS_DIR = DATA_DIR / "learning_sessions"

RULE_BASE_PATH = DATA_DIR / "rule_base.json"
RULES_BOOK_PATH = DATA_DIR / "reconstructed_rules_book.md"
RULE_DISCOVERY_CACHE = DATA_DIR / "rule_discovery_cache.json"

# When running against a Volume, the package ships seed data locally; expose its
# location so callers can seed an empty Volume on first run if they wish.
PACKAGE_DATA_DIR = PACKAGE_DIR / "data"
PACKAGE_EXEMPLARY_DIR = PACKAGE_DIR / "exemplary_data"


# ---------------------------------------------------------------------------
# IO helpers (wrap pathlib/open so the backend can be swapped in one place)
# ---------------------------------------------------------------------------


def ensure_dir(path: Path | str) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def exists(path: Path | str) -> bool:
    return Path(path).exists()


def list_dir(path: Path | str) -> list[Path]:
    p = Path(path)
    if not p.exists():
        return []
    return sorted(p.iterdir())


def read_text(path: Path | str, encoding: str = "utf-8") -> str:
    with open(path, encoding=encoding) as f:
        return f.read()


def write_text(path: Path | str, content: str, encoding: str = "utf-8") -> None:
    p = Path(path)
    ensure_dir(p.parent)
    with open(p, "w", encoding=encoding) as f:
        f.write(content)


def read_bytes(path: Path | str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def write_bytes(path: Path | str, data: bytes) -> None:
    p = Path(path)
    ensure_dir(p.parent)
    with open(p, "wb") as f:
        f.write(data)


def read_json(path: Path | str) -> Any:
    return json.loads(read_text(path))


def write_json(path: Path | str, obj: Any, indent: int = 2) -> None:
    write_text(path, json.dumps(obj, indent=indent, ensure_ascii=False))


def rmtree(path: Path | str) -> None:
    p = Path(path)
    if p.exists():
        shutil.rmtree(p)
