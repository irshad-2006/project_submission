"""Shared helpers for the Streamlit campus tools suite.

All three tools (Deadline Ledger, Campus Marquee, Case Board) persist
their data as plain JSON files under ./data so state survives across
Streamlit reruns and app restarts, without needing a database.
"""

import json
import os
import uuid
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)


def load_json(filename: str, default):
    """Load a JSON file from the data directory, returning `default` if missing/corrupt."""
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def save_json(filename: str, data) -> None:
    """Write data to a JSON file in the data directory."""
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def new_id(prefix: str = "id") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")
