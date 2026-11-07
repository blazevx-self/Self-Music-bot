from html import escape
from contextlib import suppress

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from aiogram.exceptions import TelegramBadRequest

from dependency_injector.wiring import Provide, inject

from src.containers import Container
from src.configs.yaml_loader import cfg

from src.types.user_entity import UserData

from src.services.common.search import SearchService
from src.services.common.downloader import DownloaderService
from src.bot.utils import send_track_to_chat, parse_callback_id  # parse_callback_id — вместо int(...split) с риском ValueError
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
    downloader: DownloaderService = Provide[Container.downloader_service],
):
    source_id = parse_callback_id(callback.data)  # None при "srch:abc" вместо ValueError
    if source_id is None:
        await callback.answer()
        return

    track = search_service.get_remembered(user.telegram_id, source_id)

    if track is None:
        with suppress(TelegramBadRequest):
            await callback.answer("😔 Трек не найден, поищи ещё раз.", show_alert=True)

        if callback.message:
            await callback.message.reply(
                "Этот поиск устарел. Напиши название песни заново "
                "<tg-emoji emoji-id=\"5875220935409144484\">🎵</tg-emoji>"
            )
        return  # return за пределами with — иначе reply ниже мёртвый (баг)

    await send_track_to_chat(callback, track, downloader, file_cache)

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
    page = parse_callback_id(callback.data)  # None при "spage:мусор" вместо ValueError
    if page is None:
        await callback.answer()
        return

    await callback.answer()

    query, chunk, total = search_service.page(user.telegram_id, page, PER_PAGE)

    if not chunk:
        return

    texts = cfg["message"]["search"]

    await callback.message.edit_text(
        texts["title"].format(query=escape(query)),
        reply_markup=search_keyboard(chunk, page=page, total=total)
    )
