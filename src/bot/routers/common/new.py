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
from src.bot.utils import send_track_to_chat, parse_callback_id

router = Router()

def _new_markup(chunk, page: int, total: int):
    texts = cfg["message"]["new"]

    return tracks_keyboard(
        chunk,
        page=page,
        total=total,
        item_prefix="new",
        page_prefix="npage",
        back_callback="menu:back",
        back_text=texts["buttons"]["back"],
    )

@router.callback_query(F.data == "menu:new")
@inject
async def open_new(
    callback: CallbackQuery,
    new_service: NewReleasesService = Provide[Container.new_service],
):
    texts = cfg["message"]["new"]

    if not new_service.is_loaded:
        await callback.answer(texts["updating"])
    else:
        await callback.answer()

    if not callback.message:
        return

    tracks = await new_service.get_tracks()

    if not tracks:
        await callback.message.edit_text(
            texts["empty"],
            reply_markup=_new_markup([], page=0, total=0),
        )
        return

    chunk, total = new_service.page(page=0, per_page=PER_PAGE)

    await callback.message.edit_text(
        texts["title"],
        reply_markup=_new_markup(chunk, page=0, total=total),
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
    page = parse_callback_id(callback.data)

    if page is None:
        await callback.answer()
        return

    await callback.answer()

    if not callback.message:
        return

    chunk, total = new_service.page(page, PER_PAGE)

    if not chunk:
        return  # страница вне диапазона (например, кэш обновился и список стал короче)

    await callback.message.edit_text(
        cfg["message"]["new"]["title"],
        reply_markup=_new_markup(chunk, page=page, total=total),
    )

@router.callback_query(F.data.startswith("new:"))
@inject
async def new_track(
    callback: CallbackQuery,
    new_service: NewReleasesService = Provide[Container.new_service],
    downloader: DownloaderService = Provide[Container.downloader_service],
    file_cache: TrackFileCache = Provide[Container.file_cache]
):
    source_id = parse_callback_id(callback.data)

    if source_id is None:
        await callback.answer()
        return

    track = new_service.get_by_id(source_id)

    if track is None:
        # У юзера на экране старый список, а кэш уже обновился
        with suppress(TelegramBadRequest):
            await callback.answer("🔄 Список новинок обновился — открой «Новинки» заново", show_alert=True)
        return

    await send_track_to_chat(callback, track, downloader, file_cache)