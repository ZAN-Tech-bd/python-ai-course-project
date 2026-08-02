"""Tiny helper to persist the Gemini API key locally (plain JSON, gitignored)
so the user doesn't have to repaste it every run."""

from __future__ import annotations

import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config_local.json"


def load_api_key() -> str:
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            return data.get("gemini_api_key", "")
        except (json.JSONDecodeError, OSError):
            return ""
    return ""


def save_api_key(api_key: str) -> None:
    CONFIG_PATH.write_text(json.dumps({"gemini_api_key": api_key}), encoding="utf-8")


def clear_api_key() -> None:
    if CONFIG_PATH.exists():
        CONFIG_PATH.unlink()
