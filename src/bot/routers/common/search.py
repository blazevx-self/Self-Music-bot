import tempfile

from html import escape
from pathlib import Path
from contextlib import suppress

from aiogram import F, Router
from aiogram.types import CallbackQuery, FSInputFile, Message, URLInputFile
from aiogram.exceptions import TelegramBadRequest

from dependency_injector.wiring import Provide, inject

from src.containers import Container
from src.configs.yaml_loader import cfg

from src.types.user_entity import UserData

from src.services.common.search import SearchService
from src.bot.keyboards.common.search import PER_PAGE, search_keyboard

router = Router()

@router.message(F.text, ~F.text.startswith("/"))
@inject
async def search_text(
    message: Message,
    user: UserData,
    search_service: SearchService = Provide[Container.search_service],
):
    texts = cfg["message"]["search"]
    status = await message.answer(texts["looking"])

    tracks = await search_service.search(message.text)
    search_service.remember(user.telegram_id, message.text, tracks)

    if not tracks:
        await status.edit_text(texts["empty"])
        return

    chunk = tracks[:PER_PAGE]

    await status.edit_text(
        texts["title"].format(query=escape(message.text)),
        reply_markup=search_keyboard(chunk, page=0, total=len(tracks))
    )

@router.callback_query(F.data.startswith("srch:"))
@inject
async def send_track(
    callback: CallbackQuery,
    user: UserData,
    search_service: SearchService = Provide[Container.search_service],
):
    source_id = int(callback.data.split(":")[1])
    track = search_service.get_remembered(user.telegram_id, source_id)

    if track is None:
        with suppress(TelegramBadRequest):
            await callback.answer("😔 Трек не найден, поищи ещё раз.", show_alert=True)
            return

        if callback.message:
            await callback.message.reply(
                "Этот поиск устарел. Напиши название песни заново "
                "<tg-emoji emoji-id=\"5875220935409144484\">🎵</tg-emoji>"
            )

    with suppress(TelegramBadRequest):
        await callback.answer("⏳ Скачиваю...", show_alert=False)

    thumb = (
        URLInputFile(track.cover_url, filename="cover.jpg")
        if track.cover_url
        else None
    )

    with tempfile.TemporaryDirectory(prefix="music_") as tmpdir:
        file_path = await search_service.download_track(track.artist, track.title, Path(tmpdir))

        if not file_path or not file_path.exists():
            await callback.message.answer(
                "<tg-emoji emoji-id=\"5827991357603450841\">😢</tg-emoji> "
                "Не удалось скачать трек."
            )
            return

        if callback.message:
            await callback.message.answer_audio(
                audio=FSInputFile(file_path, filename=f"{track.artist} - {track.title}{file_path.suffix}"),
                title=track.title,
                performer=track.artist,
                duration=track.duration_sec,
                thumbnail=thumb
            )

@router.callback_query(F.data == "spage:noop")
async def page_noop(callback: CallbackQuery):
    await callback.answer()

@router.callback_query(F.data.startswith("spage:"))
@inject
async def search_page(
    callback: CallbackQuery,
    user: UserData,
    search_service: SearchService = Provide[Container.search_service],
):
    await callback.answer()

    page = int(callback.data.split(":")[1])
    query, chunk, total = search_service.page(user.telegram_id, page, PER_PAGE)

    if not chunk:
        return

    texts = cfg["message"]["search"]

    await callback.message.edit_text(
        texts["title"].format(query=escape(query)),
        reply_markup=search_keyboard(chunk, page=page, total=total)
    )