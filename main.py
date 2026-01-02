from pathlib import Path
import yt_dlp

def download_best_audio(url: str, out_dir: str = "downloads") -> Path:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(out_path / "%(title)s.%(ext)s"),
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        title = info.get("title", "output")
        ext = info.get("ext", "webm")
        return out_path / f"{title}.{ext}"


def main():
    print("🎵 YouTube → Best Audio (Opus)")
    print("------------------------------")

    url = input("Enter YouTube URL: ").strip()

    if not url:
        print("❌ No URL provided.")
        return

    try:
        audio_file = download_best_audio(url)
        print(f"\n✅ Saved successfully:\n{audio_file}")
    except Exception as e:
        print("\n❌ Error:")
        print(e)


if __name__ == "__main__":
    main()
