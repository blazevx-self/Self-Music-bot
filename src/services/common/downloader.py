import asyncio
import yt_dlp

from pathlib import Path
from typing import Any

from src.utils.logger import system_logger

# Лимит Telegram Bot API на отправку файлов (около 50 МБ)
MAX_FILE_SIZE = 49 * 1024 * 1024

class DownloaderService:
    """
    Сервис загрузки аудиофайлов через yt-dlp с ограничением конкурентности.
    """

    def __init__(self, max_concurrent: int = 4) -> None:
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def download(self, artist: str, title: str, dest_dir: Path) -> Path | None:
        query = f"{artist} - {title}"
        out_tmpl = str(dest_dir / "%(id)s.%(ext)s")

        # noinspection SpellCheckingInspection
        ydl_opts: Any = {
            "format": "bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio",
            "outtmpl": out_tmpl,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "concurrent_fragment_downloads": 8,
            "buffersize": 1024 * 32,
            "extractor_args": {"youtube": {"player_client": ["mweb"]}},
        }

        def _download() -> Path | None:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                for source in (f"scsearch1:{query}", f"ytsearch1:{query} audio"):
                    try:
                        info: Any = ydl.extract_info(source, download=True)

                        if info and info.get("entries"):
                            return Path(ydl.prepare_filename(info["entries"][0]))
                    except Exception:
                        continue
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