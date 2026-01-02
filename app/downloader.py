from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Literal
import shutil

import yt_dlp

from .config import MP3_BITRATE_KBPS

StatusCb = Callable[[str], None]
ProgressCb = Callable[[float], None]  # 0.0 .. 100.0

OutputFormat = Literal["best", "mp3"]


@dataclass
class DownloadResult:
    file_path: Path
    title: str
    ext: str


class AudioDownloader:
    """
    Downloads the best available audio stream from a YouTube URL.

    - output_format="best": saves best audio stream (no ffmpeg needed)
    - output_format="mp3": converts to mp3 via ffmpeg (ffmpeg required)
    """

    def __init__(
        self,
        out_dir: Path,
        status_cb: Optional[StatusCb] = None,
        progress_cb: Optional[ProgressCb] = None,
    ) -> None:
        self.out_dir = out_dir
        self.status_cb = status_cb
        self.progress_cb = progress_cb
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def download_audio(self, url: str, output_format: OutputFormat = "best") -> DownloadResult:
        if output_format == "mp3":
            self._ensure_ffmpeg_available()

        ydl_opts = self._build_ydl_opts(output_format)

        self._emit_status("Preparing download…")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        title = info.get("title", "output")
        video_id = info.get("id", "unknown")
        if output_format == "mp3":
            ext = "mp3"
        else:
            ext = info.get("ext", "webm")

        file_path = self.out_dir / f"{title} [{video_id}].{ext}"

        self._emit_status("Done.")
        self._emit_progress(100.0)
        return DownloadResult(file_path=file_path, title=title, ext=ext)

    def _build_ydl_opts(self, output_format: OutputFormat) -> dict:
        outtmpl = str(self.out_dir / "%(title)s [%(id)s].%(ext)s")

        opts: dict = {
            "format": "bestaudio/best",
            "outtmpl": outtmpl,
            "noplaylist": True,
            "windowsfilenames": True,
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [self._progress_hook],
        }

        if output_format == "mp3":
            opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": str(MP3_BITRATE_KBPS),  # e.g. "320"
                }
            ]

        return opts

    def _ensure_ffmpeg_available(self) -> None:
        ffmpeg = shutil.which("ffmpeg")
        ffprobe = shutil.which("ffprobe")
        if not ffmpeg or not ffprobe:
            raise RuntimeError(
                "FFmpeg is required for MP3 conversion but was not found on PATH.\n\n"
                "Install FFmpeg and ensure 'ffmpeg' and 'ffprobe' are available in your terminal.\n"
                "Then restart the app."
            )

    def _progress_hook(self, d: dict) -> None:
        status = d.get("status")

        if status == "downloading":
            downloaded = d.get("downloaded_bytes") or 0
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0

            if total > 0:
                pct = (downloaded / total) * 100.0
                self._emit_progress(pct)

            speed = d.get("speed")
            eta = d.get("eta")

            msg_parts = []
            if total > 0:
                msg_parts.append(f"{(downloaded/1_048_576):.2f} / {(total/1_048_576):.2f} MiB")
            else:
                msg_parts.append(f"{(downloaded/1_048_576):.2f} MiB")

            if speed:
                msg_parts.append(f"@ {(speed/1_048_576):.2f} MiB/s")
            if eta is not None:
                msg_parts.append(f"ETA {eta}s")

            self._emit_status("Downloading: " + " ".join(msg_parts))

        elif status == "finished":
            self._emit_status("Download finished. Finalizing…")

    def _emit_status(self, msg: str) -> None:
        if self.status_cb:
            self.status_cb(msg)

    def _emit_progress(self, pct: float) -> None:
        if self.progress_cb:
            self.progress_cb(max(0.0, min(100.0, pct)))
