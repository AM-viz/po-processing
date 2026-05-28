"""
Configuration for the Invoice Processing learning core.

Data paths come from the storage abstraction (``core/storage.py``), which
honors the ``VOLUME_BASE`` env var (Databricks Volumes) with a local-fs
fallback. LLM config targets AWS Bedrock (see ``core/llm_client.py``).
"""

import sys

from . import storage
from .llm_client import (
    get_aws_region,
    get_call_delay,
    get_max_tokens,
    get_sonnet_model_id,
    model_id_for_role,
)

# ---------------------------------------------------------------------------
# Directory layout (re-exported from the storage abstraction)
# ---------------------------------------------------------------------------

AGENT_PKG_DIR = storage.PACKAGE_DIR  # invoice_processing/ (package root)
CORE_DIR = AGENT_PKG_DIR / "core"
PROJECT_ROOT = storage.PROJECT_ROOT

DATA_DIR = storage.DATA_DIR
AGENTIC_FLOW_OUT = storage.AGENTIC_FLOW_OUT
ALF_OUT_DIR = storage.ALF_OUT_DIR
RULE_BASE_PATH = storage.RULE_BASE_PATH
RULES_BOOK_PATH = storage.RULES_BOOK_PATH
SESSIONS_DIR = storage.SESSIONS_DIR

# Legacy aliases (for backward compatibility within modules)
LEARNING_AGENT_DIR = AGENT_PKG_DIR

# ---------------------------------------------------------------------------
# Ensure shared_libraries is importable
# ---------------------------------------------------------------------------

_shared_libs_str = str(AGENT_PKG_DIR / "shared_libraries")
if _shared_libs_str not in sys.path:
    sys.path.insert(0, _shared_libs_str)

# ---------------------------------------------------------------------------
# LLM configuration (AWS Bedrock; mirrors acting_agent / alf_engine.py)
# ---------------------------------------------------------------------------


def get_llm_model():
    """Return the Bedrock model id for the heavy (reasoning) role."""
    return get_sonnet_model_id()


def get_llm_model_for_role(role: str = "heavy"):
    """Return the Bedrock model id for a logical role ("fast" / "heavy")."""
    return model_id_for_role(role)


def get_llm_region():
    """Return the configured AWS region for Bedrock."""
    return get_aws_region()


def get_llm_call_delay():
    """Return optional inter-call throttle delay in seconds (default 0)."""
    return get_call_delay()


def get_llm_max_tokens():
    """Return the configured Bedrock max output tokens."""
    return get_max_tokens()

# ---------------------------------------------------------------------------
# Master data loader (optional — provides domain-agnostic configuration)
# ---------------------------------------------------------------------------

try:
    from ..shared_libraries.master_data_loader import load_master_data

    _master = load_master_data()
    _MASTER_DATA = _master
except Exception:
    _MASTER_DATA = None

# ---------------------------------------------------------------------------
# Artifact file mapping (agent output folder -> context key)
# Reads from master data if available, else uses hardcoded defaults.
# ---------------------------------------------------------------------------

if _MASTER_DATA and _MASTER_DATA.get_agent_file_map():
    _md_map = _MASTER_DATA.get_agent_file_map()
    ARTIFACT_MAP = {}
    for key, filename in _md_map.items():
        # Normalize master data keys to match what case_loader expects
        if key == "final_decision":
            ARTIFACT_MAP["decision"] = filename
        elif key == "transformation":
            ARTIFACT_MAP["transformer"] = filename
        else:
            ARTIFACT_MAP[key] = filename
else:
    ARTIFACT_MAP = {
        "classification": "01_classification.json",
        "extraction": "02_extraction.json",
        "phase1": "03_phase1_validation.json",
        "phase2": "04_phase2_validation.json",
        "phase3": "05_phase3_validation.json",
        "phase4": "06_phase4_validation.json",
        "transformer": "07_transformation.json",
        "decision": "08_decision.json",
        "audit_log": "09_audit_log.json",
        "postprocessing": "Postprocessing_Data.json",
    }

# ---------------------------------------------------------------------------
# Terminal formatting helpers
# ---------------------------------------------------------------------------


class Color:
    """ANSI color codes for terminal output."""

    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
