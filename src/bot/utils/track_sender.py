import tempfile

from contextlib import suppress
from pathlib import Path

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, FSInputFile, URLInputFile

from src.services.common.downloader import DownloaderService
from src.services.common.track_cache import TrackFileCache
from src.types.track import TrackData


async def send_track_to_chat(
    callback: CallbackQuery,
    track: TrackData,
    downloader: DownloaderService,
    file_cache: TrackFileCache,
) -> None:
    """
    Отправляет трек в чат как Telegram Audio (общий сценарий поиска и «Новинок»).

    Сначала пробует file_id из кэша — тогда трек улетает мгновенно, без yt-dlp
    и без загрузки файла. Если кэша нет или file_id устарел — скачивает файл,
    отправляет его с обложкой и кладёт полученный file_id в кэш.
    """
    # 1. Пробуем кэш: повторная отправка по file_id
    cached = file_cache.get(track)

    if cached:
        await callback.answer()
        try:
            # По file_id нельзя прицепить thumbnail — обложка будет только у первой отправки файла
            await callback.message.answer_audio(
                audio=cached,
                title=track.title,
                performer=track.artist,
                duration=track.duration_sec,
            )
            return
        except TelegramBadRequest:
            file_cache.drop(track)  # file_id устарел → п.2, скачаем заново

    # 2. Кэша нет — скачиваем через yt-dlp
    with suppress(TelegramBadRequest):
        await callback.answer("⏳ Скачиваю...", show_alert=False)

    thumb = URLInputFile(track.cover_url, filename="cover.jpg") if track.cover_url else None

    with tempfile.TemporaryDirectory(prefix="music_") as tmpdir:
        # expected_duration_sec: отсекаем скачанные 30-секундные превью вместо полной версии
        file_path = await downloader.download(
            track.artist, track.title, Path(tmpdir),
            expected_duration_sec=track.duration_sec,
        )

        if not file_path or not downloader.is_size_ok(file_path):
            await callback.message.answer(
                "<tg-emoji emoji-id=\"5827991357603450841\">😢</tg-emoji> "
                "Не удалось скачать трек."
            )
            return

        if callback.message:
            sent = await callback.message.answer_audio(
                audio=FSInputFile(
                    file_path,
                    filename=f"{track.artist} - {track.title}{file_path.suffix}",
                ),
                title=track.title,
                performer=track.artist,
                duration=track.duration_sec,
                thumbnail=thumb,
            )

            # 3. Кладём file_id в кэш — следующие запросы этого трека уйдут мгновенно
            if sent and sent.audio:
                file_cache.put(track, sent.audio.file_id)
