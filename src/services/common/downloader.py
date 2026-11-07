import asyncio
import shutil
import yt_dlp

from pathlib import Path
from typing import Any

from src.utils.logger import system_logger

# Лимит Telegram Bot API на отправку файлов (около 50 МБ)
MAX_FILE_SIZE = 49 * 1024 * 1024
MAX_DURATION_DIFF = 15

class DownloaderService:
    """
    Сервис загрузки аудиофайлов через yt-dlp с ограничением конкурентности.
    """

    def __init__(self, max_concurrent: int = 4) -> None:
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def download(
        self,
        artist: str,
        title: str,
        dest_dir: Path,
        expected_duration_sec: int | None = None
    ) -> Path | None:
        query = f"{artist} - {title}"
        out_tmpl = str(dest_dir / "%(id)s.%(ext)s")

        has_ffmpeg = shutil.which("ffmpeg") is not None

        # noinspection SpellCheckingInspection
        ydl_opts: Any = {
            "format": "bestaudio/best" if has_ffmpeg else "bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio",
            "outtmpl": out_tmpl,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 15,
            "retries": 2,
            "concurrent_fragment_downloads": 8,
            "buffersize": 1024 * 32,
            "source_address": "0.0.0.0",
            "extractor_args": {"youtube": {"player_client": ["mweb", "android", "web"]}},
        }

        if has_ffmpeg:
            ydl_opts["postprocessors"] = [
                {"key": "FFmpegExtractAudio", "preferredcodec": "m4a", "preferredquality": "192"}
            ]

        def _download() -> Path | None:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                for source in (f"scsearch3:{query}", f"ytsearch3:{query} audio"):
                    try:
                        search: Any = ydl.extract_info(source, download=False)
                    except Exception:
                        continue

                    for entry in (search or {}).get("entries") or []:
                        url = entry.get("webpage_url") or entry.get("url")

                        if not url:
                            continue

                        try:
                            info: Any = ydl.extract_info(url, download=True)
                        except Exception:
                            continue

                        if info:
                            dur = info.get("duration") or 0

                            if expected_duration_sec and dur and abs(dur - expected_duration_sec) > MAX_DURATION_DIFF:
                                system_logger.warning(
                                    f"[DOWNLOAD] skip {url} | duration={dur}s != expected={expected_duration_sec}s"
                                )
                                continue

                            path = Path(ydl.prepare_filename(info))
                            return path.with_suffix(".m4a") if has_ffmpeg else path
            return None

        try:
            async with self._semaphore:
                return await asyncio.to_thread(_download)
        except Exception as e:
            system_logger.error(f"[DOWNLOAD] Error yt-dlp for «{query}»: {e}")
            return None

    @staticmethod
    def is_size_ok(path: Path) -> bool:
        try:
            return path.exists() and path.stat().st_size <= MAX_FILE_SIZE
        except OSError:
            return False