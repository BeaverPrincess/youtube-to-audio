from pathlib import Path

APP_TITLE = "YouTube → Audio"
DEFAULT_OUTPUT_DIR = Path("downloads")
WINDOW_MIN_SIZE = (640, 420)
POLL_MS = 100

OUTPUT_FORMATS = [
    ("Best (original)", "best"),
    ("MP3 (requires FFmpeg)", "mp3"),
]
DEFAULT_OUTPUT_FORMAT = "best"
MP3_BITRATE_KBPS = 320