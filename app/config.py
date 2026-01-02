# app/config.py
from pathlib import Path
import sys
import os

APP_TITLE = "YouTube → Audio"
WINDOW_MIN_SIZE = (640, 420)
POLL_MS = 100

OUTPUT_SUBDIR_NAME = "downloaded_audios"

# Default base folder for saving
# Prefer Windows Downloads if it exists fallback to home.
def _default_save_root() -> Path:
    home = Path.home()
    downloads = home / "Downloads"
    return downloads if downloads.exists() else home

DEFAULT_SAVE_ROOT = _default_save_root()

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

OUTPUT_FORMATS = [
    ("Best (original)", "best"),
    ("MP3 (requires FFmpeg)", "mp3"),
]
DEFAULT_OUTPUT_FORMAT = "best"
MP3_BITRATE_KBPS = 320
