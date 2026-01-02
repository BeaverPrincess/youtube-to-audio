from pathlib import Path
import sys

APP_TITLE = "YouTube → Audio"
DEFAULT_OUTPUT_DIR = Path("downloads")
WINDOW_MIN_SIZE = (640, 420)
POLL_MS = 100

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