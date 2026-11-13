import asyncio
import tempfile
from html import escape
from io import BytesIO
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.types import Message
from dependency_injector.wiring import Provide, inject

from src.bot.keyboards.common.search import PER_PAGE, search_keyboard
from src.configs.yaml_loader import cfg
from src.containers import Container
from src.services.common.search import SearchService
from src.services.common.settings import SettingsService
from src.services.external.audd import AudDClient
from src.types.user_entity import UserData
from src.utils.logger import system_logger

router = Router()

MAX_SOURCE_BYTES = 20 * 1024 * 1024
MAX_AUDIO_BYTES = 9 * 1024 * 1024
VIDEO_CLIP_SECONDS = 30


def _media_info(message: Message) -> tuple[str, str, int | None, bool, bool] | None:
    """Return file id, filename, size, is_video and is_humming for supported Telegram media."""
    if message.voice:
        return message.voice.file_id, "voice.ogg", message.voice.file_size, False, True
    if message.audio:
        return (
            message.audio.file_id,
            message.audio.file_name or "audio",
            message.audio.file_size,
            False,
            False,
        )
    if message.video:
        return message.video.file_id, "video.mp4", message.video.file_size, True, False
    if message.video_note:
        return message.video_note.file_id, "video_note.mp4", message.video_note.file_size, True, True
    if message.document:
        mime = (message.document.mime_type or "").lower()
        filename = message.document.file_name or "audio"
        suffix = Path(filename).suffix.lower()
        is_video = mime.startswith("video/") or suffix in {".mp4", ".mov", ".mkv", ".webm"}
        is_audio = mime.startswith("audio/") or suffix in {
            ".mp3", ".m4a", ".aac", ".ogg", ".oga", ".opus", ".wav", ".flac", ".webm",
        }
        if is_video or is_audio:
            return (
                message.document.file_id,
                filename,
                message.document.file_size,
                is_video,
                False,
            )
    return None


async def _video_to_audio(data: bytes, filename: str) -> bytes | None:
    """Extract at most 30 seconds of mono MP3 so the recognition API receives audio, not video."""
    suffix = Path(filename).suffix or ".mp4"
    try:
        with tempfile.TemporaryDirectory(prefix="recognition_") as directory:
            source = Path(directory) / f"source{suffix}"
            target = Path(directory) / "clip.mp3"
            source.write_bytes(data)

            process = await asyncio.create_subprocess_exec(
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(source),
                "-vn",
                "-t",
                str(VIDEO_CLIP_SECONDS),
                "-ac",
                "1",
                "-ar",
                "22050",
                "-b:a",
                "96k",
                str(target),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                _, stderr = await asyncio.wait_for(process.communicate(), timeout=20)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                system_logger.warning("[RECOGNITION] ffmpeg timed out")
                return None

            if process.returncode != 0 or not target.is_file():
                system_logger.warning(
                    f"[RECOGNITION] ffmpeg failed | exit={process.returncode} | "
                    f"error={stderr.decode(errors='replace')[:200]}"
                )
                return None
            return target.read_bytes()
    except (OSError, FileNotFoundError) as exc:
        system_logger.warning(f"[RECOGNITION] video audio extraction failed | error={exc}")
        return None


@router.message(F.voice | F.audio | F.video | F.video_note | F.document)
@inject
async def recognize_media(
    message: Message,
    user: UserData,
    bot: Bot,
    settings_service: SettingsService = Provide[Container.settings_service],
    audd: AudDClient = Provide[Container.audd_client],
    search_service: SearchService = Provide[Container.search_service],
):
    """Recognize a voice recording, audio file, or video and search the result in Deezer."""
    texts = cfg["message"]["recognition"]

    if not settings_service.is_enabled(user, "recognize"):
        await message.answer(texts["disabled"])
        return
    if not audd.configured:
        await message.answer(texts["not_configured"])
        return

    info = _media_info(message)
    if info is None:
        await message.answer(texts["unsupported"])
        return

    file_id, filename, size, is_video, is_humming = info
    max_size = MAX_SOURCE_BYTES if is_video else MAX_AUDIO_BYTES
    if size is not None and size > max_size:
        await message.answer(texts["too_large"])
        return

    progress = await message.answer(texts["checking"])
    try:
        telegram_file = await bot.get_file(file_id)
        if not telegram_file.file_path:
            await progress.edit_text(texts["file_error"])
            return
        buffer = BytesIO()
        await bot.download_file(telegram_file.file_path, destination=buffer)
        media = buffer.getvalue()
    except Exception as exc:
        system_logger.warning(f"[RECOGNITION] Telegram download failed | error={exc}")
        await progress.edit_text(texts["file_error"])
        return

    if not media or len(media) > max_size:
        await progress.edit_text(texts["too_large"] if media else texts["file_error"])
        return

    if is_video:
        media = await _video_to_audio(media, filename) or b""
        filename = "video-audio.mp3"
    if not media or len(media) > MAX_AUDIO_BYTES:
        await progress.edit_text(texts["file_error"] if not media else texts["too_large"])
        return

    status, matches = await audd.recognize(media, filename, humming=is_humming)
    if status == "error":
        await progress.edit_text(texts["service_error"])
        return
    if not matches:
        await progress.edit_text(texts["not_found"])
        return

    match = matches[0]
    query = f"{match.artist} {match.title}"
    escaped_artist = escape(match.artist)
    escaped_title = escape(match.title)
    tracks = await search_service.search(query)
    search_service.remember(user.telegram_id, query, tracks)

    if not tracks:
        await progress.edit_text(
            texts["recognized_no_results"].format(
                artist=escaped_artist,
                title=escaped_title,
            )
        )
        return

    await progress.edit_text(
        texts["recognized"].format(artist=escaped_artist, title=escaped_title),
        reply_markup=search_keyboard(tracks[:PER_PAGE], page=0, total=len(tracks)),
    )
