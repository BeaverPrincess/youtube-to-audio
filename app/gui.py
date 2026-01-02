# app/gui.py
from __future__ import annotations

import threading
import queue
from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from .config import (
    APP_TITLE,
    WINDOW_MIN_SIZE,
    POLL_MS,
    OUTPUT_FORMATS,
    DEFAULT_OUTPUT_FORMAT,
    OUTPUT_SUBDIR_NAME,
)
from .downloader import AudioDownloader, DownloadResult, OutputFormat
from .settings import load_settings, save_settings, AppSettings


@dataclass
class UiEvent:
    kind: str  # "status" | "progress" | "done" | "error"
    payload: object


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.minsize(*WINDOW_MIN_SIZE)

        self._events: "queue.Queue[UiEvent]" = queue.Queue()
        self._worker: threading.Thread | None = None

        # NEW: settings (persistent)
        self.settings: AppSettings = load_settings()

        self._build_widgets()
        self._layout_widgets()

        # Ensure output dir exists at startup
        self._ensure_output_dir()

        self.after(POLL_MS, self._poll_events)

    # ---------- Output directory handling ----------

    def _get_output_dir(self) -> Path:
        # Always save into <save_root>/downloaded_audios
        return Path(self.settings.save_root) / OUTPUT_SUBDIR_NAME

    def _ensure_output_dir(self) -> None:
        out_dir = self._get_output_dir()
        out_dir.mkdir(parents=True, exist_ok=True)

    def _choose_save_root(self) -> None:
        if self._worker and self._worker.is_alive():
            messagebox.showinfo("Busy", "Please wait for the current download to finish.")
            return

        initial = str(self.settings.save_root) if self.settings.save_root else str(Path.home())
        chosen = filedialog.askdirectory(title="Choose save location", initialdir=initial)

        if not chosen:
            return

        self.settings.save_root = Path(chosen)
        save_settings(self.settings)

        # Create downloaded_audios inside the new location
        self._ensure_output_dir()

        self.save_path_var.set(str(self._get_output_dir()))
        self._append_log(f"📁 Save location set to: {self._get_output_dir()}")
        self._set_status("Save location updated.")

    # ---------- UI ----------

    def _build_widgets(self) -> None:
        self.main = ttk.Frame(self, padding=12)

        self.header = ttk.Label(
            self.main,
            text="YouTube → Audio Downloader",
            font=("Segoe UI", 14, "bold"),
        )

        self.url_label = ttk.Label(self.main, text="YouTube URL:")
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(self.main, textvariable=self.url_var)
        self.url_entry.focus_set()

        # Output format dropdown
        self.format_label = ttk.Label(self.main, text="Format:")
        self.format_var = tk.StringVar(value=DEFAULT_OUTPUT_FORMAT)

        self._format_label_to_value = {label: value for (label, value) in OUTPUT_FORMATS}
        self._format_value_to_label = {value: label for (label, value) in OUTPUT_FORMATS}

        self.format_combo = ttk.Combobox(
            self.main,
            state="readonly",
            values=[label for (label, _v) in OUTPUT_FORMATS],
        )
        self.format_combo.set(self._format_value_to_label[DEFAULT_OUTPUT_FORMAT])

        # NEW: Save location row
        self.save_label = ttk.Label(self.main, text="Save to:")
        self.save_path_var = tk.StringVar(value=str(self._get_output_dir()))
        self.save_path_entry = ttk.Entry(
            self.main,
            textvariable=self.save_path_var,
            state="readonly",
        )
        self.choose_btn = ttk.Button(self.main, text="Choose…", command=self._choose_save_root)

        self.convert_btn = ttk.Button(self.main, text="Download", command=self.on_convert_clicked)

        self.progress = ttk.Progressbar(self.main, orient="horizontal", mode="determinate", maximum=100)
        self.status_var = tk.StringVar(value="Ready.")
        self.status_label = ttk.Label(self.main, textvariable=self.status_var)

        self.log = tk.Text(self.main, height=10, wrap="word", state="disabled")
        self.log_scroll = ttk.Scrollbar(self.main, command=self.log.yview)
        self.log.configure(yscrollcommand=self.log_scroll.set)

        self.bind("<Return>", lambda _e: self.on_convert_clicked())

    def _layout_widgets(self) -> None:
        self.main.grid(row=0, column=0, sticky="nsew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.main.grid_columnconfigure(1, weight=1)

        self.header.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 12))

        # URL row
        self.url_label.grid(row=1, column=0, sticky="w")
        self.url_entry.grid(row=1, column=1, sticky="ew", padx=(8, 8))
        self.convert_btn.grid(row=1, column=2, sticky="e")

        # Format row
        self.format_label.grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.format_combo.grid(row=2, column=1, sticky="w", pady=(8, 0))

        # NEW: Save row
        self.save_label.grid(row=3, column=0, sticky="w", pady=(8, 0))
        self.save_path_entry.grid(row=3, column=1, sticky="ew", padx=(8, 8), pady=(8, 0))
        self.choose_btn.grid(row=3, column=2, sticky="e", pady=(8, 0))

        self.progress.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(12, 6))
        self.status_label.grid(row=5, column=0, columnspan=3, sticky="w", pady=(0, 8))

        self.log.grid(row=6, column=0, columnspan=2, sticky="nsew")
        self.log_scroll.grid(row=6, column=2, sticky="nsw")
        self.main.grid_rowconfigure(6, weight=1)

    # ---------- Actions ----------

    def on_convert_clicked(self) -> None:
        if self._worker and self._worker.is_alive():
            messagebox.showinfo("Busy", "A download is already running.")
            return

        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Missing URL", "Please paste a YouTube URL first.")
            return

        fmt_label = self.format_combo.get()
        output_format: OutputFormat = self._format_label_to_value.get(fmt_label, "best")  # type: ignore

        # Ensure dir exists right before starting (in case user deleted it)
        self._ensure_output_dir()

        self._set_busy(True)
        self._set_progress(0.0)
        self._set_status("Starting…")
        self._append_log(f"URL: {url}")
        self._append_log(f"Format: {fmt_label}")
        self._append_log(f"Save to: {self._get_output_dir()}")

        self._worker = threading.Thread(
            target=self._download_worker,
            args=(url, output_format, self._get_output_dir()),
            daemon=True,
        )
        self._worker.start()

    def _download_worker(self, url: str, output_format: OutputFormat, out_dir: Path) -> None:
        def status_cb(msg: str) -> None:
            self._events.put(UiEvent("status", msg))

        def progress_cb(pct: float) -> None:
            self._events.put(UiEvent("progress", pct))

        try:
            downloader = AudioDownloader(
                out_dir=out_dir,
                status_cb=status_cb,
                progress_cb=progress_cb,
            )
            result: DownloadResult = downloader.download_audio(url, output_format=output_format)
            self._events.put(UiEvent("done", result))
        except Exception as e:
            self._events.put(UiEvent("error", str(e)))

    def _poll_events(self) -> None:
        try:
            while True:
                ev = self._events.get_nowait()
                if ev.kind == "status":
                    self._set_status(str(ev.payload))
                elif ev.kind == "progress":
                    self._set_progress(float(ev.payload))
                elif ev.kind == "done":
                    res: DownloadResult = ev.payload  # type: ignore
                    self._set_status(f"Saved: {res.file_path}")
                    self._append_log(f"✅ Saved: {res.file_path}")
                    self._set_busy(False)
                elif ev.kind == "error":
                    msg = str(ev.payload)
                    self._set_status("Error.")
                    self._append_log(f"❌ Error: {msg}")
                    messagebox.showerror("Download failed", msg)
                    self._set_busy(False)
        except queue.Empty:
            pass
        finally:
            self.after(POLL_MS, self._poll_events)

    def _set_status(self, msg: str) -> None:
        self.status_var.set(msg)

    def _set_progress(self, pct: float) -> None:
        self.progress["value"] = max(0.0, min(100.0, pct))

    def _append_log(self, msg: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        self.convert_btn.configure(state=state)
        self.url_entry.configure(state=state)
        self.choose_btn.configure(state=state)
        self.format_combo.configure(state=("disabled" if busy else "readonly"))
