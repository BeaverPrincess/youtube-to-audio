# app/settings.py
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from .config import DEFAULT_SAVE_ROOT

APP_DIR_NAME = "youtube_audio_downloader"
SETTINGS_FILE_NAME = "settings.json"


def _get_config_dir() -> Path:
    base = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
    return base / APP_DIR_NAME


def get_settings_path() -> Path:
    cfg_dir = _get_config_dir()
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir / SETTINGS_FILE_NAME


@dataclass
class AppSettings:
    save_root: Path = DEFAULT_SAVE_ROOT


def load_settings() -> AppSettings:
    path = get_settings_path()
    if not path.exists():
        return AppSettings()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        save_root = Path(data.get("save_root", str(DEFAULT_SAVE_ROOT)))
        return AppSettings(save_root=save_root)
    except Exception:
        # If file is corrupted, fall back safely
        return AppSettings()


def save_settings(settings: AppSettings) -> None:
    path = get_settings_path()
    data = {"save_root": str(settings.save_root)}
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
