import tempfile
from contextlib import suppress
from pathlib import Path

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, FSInputFile, URLInputFile

from src.services.common.downloader import DownloaderService
from src.types.track import TrackData

async def send_track_to_chat(
    callback: CallbackQuery,
    track: TrackData,
    downloader: DownloaderService,
) -> None:
    """Скачивает трек и отправляет в чат как Telegram Audio (обложка + теги + длительность)."""

    with suppress(TelegramBadRequest):
        await callback.answer("⏳ Скачиваю...", show_alert=False)

    thumb = URLInputFile(track.cover_url, filename="cover.jpg") if track.cover_url else None

    with tempfile.TemporaryDirectory(prefix="music_") as tmpdir:
        file_path = await downloader.download(track.artist, track.title, Path(tmpdir))

        if not file_path or not downloader.is_size_ok(file_path):
            await callback.message.answer(
                "<tg-emoji emoji-id=\"5827991357603450841\">😢</tg-emoji> Не удалось скачать трек."
            )
            return

        if callback.message:
            await callback.message.answer_audio(
                audio=FSInputFile(file_path, filename=f"{track.artist} - {track.title}{file_path.suffix}"),
                title=track.title,
                performer=track.artist,
                duration=track.duration_sec,
                thumbnail=thumb,
            )