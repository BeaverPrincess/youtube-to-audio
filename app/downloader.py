from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import yt_dlp


StatusCb = Callable[[str], None]
ProgressCb = Callable[[float], None]  # 0.0 .. 100.0


@dataclass
class DownloadResult:
    file_path: Path
    title: str
    ext: str


class AudioDownloader:
    """
    Downloads the best available audio stream from a YouTube URL.
    Uses yt-dlp only (no ffmpeg) and writes to out_dir.
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

    def download_best_audio(self, url: str) -> DownloadResult:
        ydl_opts = self._build_ydl_opts()

        self._emit_status("Preparing download…")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        title = info.get("title", "output")
        ext = info.get("ext", "webm")
        video_id = info.get("id", "unknown")
        file_path = self.out_dir / f"{title} [{video_id}].{ext}"

        self._emit_status("Done.")
        self._emit_progress(100.0)
        return DownloadResult(file_path=file_path, title=title, ext=ext)

    def _build_ydl_opts(self) -> dict:
        outtmpl = str(self.out_dir / "%(title)s [%(id)s].%(ext)s")

        return {
            "format": "bestaudio/best",
            "outtmpl": outtmpl,
            "noplaylist": True,
            "windowsfilenames": True,
            "quiet": True,          # keep console clean; we’ll show messages in UI
            "no_warnings": True,
            "progress_hooks": [self._progress_hook],
        }

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
