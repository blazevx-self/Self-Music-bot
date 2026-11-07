import asyncio
import shutil
from pathlib import Path
from typing import Any

import yt_dlp

from src.configs.settings import settings
from src.utils.logger import system_logger

MAX_FILE_SIZE = 49 * 1024 * 1024   # ~50 МБ — лимит Bot API на загрузку файла
DOWNLOAD_TIMEOUT = 90              # общий таймаут на скачивание одного трека, сек
MAX_DURATION_DIFF = 15             # макс. расхождение длительности результата с Deezer (сек)


class _YtdlpLogger:
    """Роутит логи yt-dlp в наш system_logger (DRM/ сетевые ошибки не сыпятся в stderr)."""

    def debug(self, msg: str) -> None:
        system_logger.debug(f"[yt-dlp] {msg}")

    def warning(self, msg: str) -> None:
        system_logger.warning(f"[yt-dlp] {msg}")

    def error(self, msg: str) -> None:
        system_logger.error(f"[yt-dlp] {msg}")


class DownloaderService:
    """
    Скачивает полную версию трека через yt-dlp.

    Источники по очереди: SoundCloud → YouTube; у каждого источника пробуем до 3
    первых результатов (первые могут быть DRM-protected или 30-секундными превью —
    тогда берём следующие). Результат с длительностью, сильно отличающейся от
    ожидаемой (из Deezer), скипается. Скачивание — в отдельном потоке, параллельные
    скачивания ограничены семафором, общий таймаут — DOWNLOAD_TIMEOUT.
    """

    def __init__(self, max_concurrent: int = 4) -> None:
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def download(
        self,
        artist: str,
        title: str,
        dest_dir: Path,
        expected_duration_sec: int | None = None,
    ) -> Path | None:
        """
        Найти и скачать трек в dest_dir.

        :param expected_duration_sec: ожидаемая длительность (из Deezer); если résultat
            отличается больше чем на MAX_DURATION_DIFF — результат считается плохим
            (например, скачалось 30-секундное превью вместо полной версии) и скипается.
        :return: Путь к скачанному файлу либо None при неудаче.
        """
        query = f"{artist} - {title}"
        out_tmpl = str(dest_dir / "%(id)s.%(ext)s")

        has_ffmpeg = shutil.which("ffmpeg") is not None

        # noinspection SpellCheckingInspection
        ydl_opts: Any = {
            # bestaudio/best: если у видео нет отдельного audio-потока (часто с mweb),
            # берём лучший combined и вырезаем аудио ffmpeg'ом в m4a
            "format": "bestaudio/best" if has_ffmpeg else "bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio",
            "outtmpl": out_tmpl,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "logger": _YtdlpLogger(),
            "socket_timeout": 15,
            "retries": 2,
            "concurrent_fragment_downloads": 8,
            "buffersize": 1024 * 32,
            "source_address": "0.0.0.0",           # форс IPv4 — лечит часть случаев Errno -5
            "proxy": settings.YTDLP_PROXY or None,  # прокси из .env, если YouTube недоступен с сервера
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
                        continue  # источник недоступен (DNS/блок) — дальше

                    entries = (search or {}).get("entries") or []

                    for entry in entries[:3]:
                        if not entry:
                            continue

                        url = entry.get("webpage_url") or entry.get("url")

                        if not url:
                            continue

                        try:
                            info: Any = ydl.extract_info(url, download=True)
                        except Exception:
                            continue  # DRM / 403 / битая запись — следующая

                        if not info:
                            continue

                        dur = info.get("duration") or 0

                        if expected_duration_sec and dur and abs(dur - expected_duration_sec) > MAX_DURATION_DIFF:
                            system_logger.warning(
                                f"[DOWNLOAD] skip {url} | duration={dur}s != expected={expected_duration_sec}s (превью?)"
                            )
                            continue

                        path = Path(ydl.prepare_filename(info))
                        return path.with_suffix(".m4a") if has_ffmpeg else path

            return None

        try:
            async with self._semaphore:
                return await asyncio.wait_for(
                    asyncio.to_thread(_download),
                    timeout=DOWNLOAD_TIMEOUT,
                )
        except asyncio.TimeoutError:
            system_logger.error(f"[DOWNLOAD] Таймаут {DOWNLOAD_TIMEOUT}с для «{query}»")
            return None
        except Exception as e:
            system_logger.error(f"[DOWNLOAD] Ошибка yt-dlp для «{query}»: {e}")
            return None

    @staticmethod
    def is_size_ok(path: Path) -> bool:
        """Файл существует и влезает в лимит Bot API (~50 МБ)."""
        try:
            return path.exists() and path.stat().st_size <= MAX_FILE_SIZE
        except OSError:
            return False
