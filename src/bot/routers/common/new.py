from html import escape
from contextlib import suppress

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery

from dependency_injector.wiring import Provide, inject

from src.containers import Container
from src.configs.yaml_loader import cfg

from src.services.common.downloader import DownloaderService
from src.services.common.new import NewReleasesService
from src.services.common.track_cache import TrackFileCache

from src.bot.keyboards.common.tracks import PER_PAGE, tracks_keyboard
from src.utils.track_sender import send_track_to_chat

router = Router()

@router.callback_query(F.data == "menu:new")
@inject
async def open_new(
    callback: CallbackQuery,
    new_service: NewReleasesService = Provide[Container.new_service],
):
    texts = cfg["message"]["new"]
    tracks = await new_service.get_tracks()

    await callback.answer()

    if not tracks:
        await callback.message.edit_text(texts["empty"])
        return

    chunk, total = new_service.page(page=0, per_page=PER_PAGE)

    await callback.message.edit_text(
        texts["title"],
        reply_markup=tracks_keyboard(
            chunk,
            page=0,
            total=total,
            item_prefix="new",
            page_prefix="npage",
            back_callback="menu:back"
        )
    )

@router.callback_query(F.data == "npage:noop")
async def new_page_noop(callback: CallbackQuery):
    await callback.answer()

@router.callback_query(F.data.startswith("npage:"))
@inject
async def new_page(
    callback: CallbackQuery,
    new_service: NewReleasesService = Provide[Container.new_service],
):
    await callback.answer()

    page = int(callback.data.split(":")[1])
    chunk, total = new_service.page(page, PER_PAGE)

    if not chunk:
        return

    await callback.message.edit_text(
        cfg["message"]["new"]["title"],
        reply_markup=tracks_keyboard(
            chunk,
            page,
            total,
            item_prefix="new",
            page_prefix="npage",
            back_callback="menu:back")
    )

@router.callback_query(F.data.startswith("new:"))
@inject
async def new_track(
    callback: CallbackQuery,
    new_service: NewReleasesService = Provide[Container.new_service],
    downloader: DownloaderService = Provide[Container.downloader_service],
    file_cache: TrackFileCache = Provide[Container.file_cache]
):
    source_id = int(callback.data.split(":")[1])
    track = new_service.get_by_id(source_id)

    if track is None:
        with suppress(TelegramBadRequest):
            await callback.answer("🔄 Список новинок обновился — открой «Новинки» заново", show_alert=True)
        return

    await send_track_to_chat(callback, track, downloader, file_cache)