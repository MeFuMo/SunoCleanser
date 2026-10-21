"""User settings (language, last parameters, custom presets) stored as JSON."""

from __future__ import annotations

import json
import locale
import os
from pathlib import Path
from typing import Any, Dict

SETTINGS_ENV = "SUNOCLEANSER_SETTINGS"
DEFAULT_SETTINGS_PATH = Path.home() / ".sunocleanser" / "settings.json"
SUPPORTED_LANGUAGES = ("en", "es")


def settings_path() -> Path:
    override = os.environ.get(SETTINGS_ENV)
    return Path(override) if override else DEFAULT_SETTINGS_PATH


def detect_language() -> str:
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var, "")
        if value:
            return "es" if value.lower().startswith("es") else "en"
    try:
        code = locale.getlocale()[0] or ""
    except ValueError:
        code = ""
    return "es" if code.lower().startswith("es") else "en"


def default_settings() -> Dict[str, Any]:
    return {
        "language": detect_language(),
        "preset": "original",
        "params": {},
        "custom_presets": {},
        "output_dir": "out",
        "last_dir": "",
        "show_advanced": False,
    }


def load_settings(path: Path | None = None) -> Dict[str, Any]:
    """Load settings, falling back to defaults for anything missing or unreadable."""
    data = default_settings()
    target = path or settings_path()
    try:
        stored = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return data
    if isinstance(stored, dict):
        for key, value in stored.items():
            if key in data and isinstance(value, type(data[key])):
                data[key] = value
    if data["language"] not in SUPPORTED_LANGUAGES:
        data["language"] = "en"
    return data


def save_settings(data: Dict[str, Any], path: Path | None = None) -> bool:
    """Write atomically; returns False instead of raising if the disk refuses."""
    target = path or settings_path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp, target)
        return True
    except OSError:
        return False
