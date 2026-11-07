from html import escape
from contextlib import suppress

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery

from dependency_injector.wiring import Provide, inject

from src.containers import Container
from src.configs.yaml_loader import cfg

from src.core.constants.pagination import PER_PAGE

from src.services.common.top import TopService
from src.services.common.downloader import DownloaderService
from src.services.common.track_cache import TrackFileCache

from src.bot.keyboards.common.tracks import tracks_keyboard
from src.bot.keyboards.common.top import genres_keyboard

from src.bot.utils import send_track_to_chat

router = Router()

@router.callback_query(F.data == "menu:top")
@inject
async def open_top(callback: CallbackQuery, top_service: TopService = Provide[Container.top_service]):
    texts = cfg["message"]["top"]

    if not top_service.genres_loaded:
        await callback.answer(texts["updating"])
    else:
        await callback.answer()

    if not callback.message:
        return

    genres = await top_service.get_genres()

    if not genres:
        await callback.message.edit_text(
            texts["empty"],
            reply_markup=genres_keyboard([], back_callback="menu:back"),
        )
        return

    await callback.message.edit_text(
        texts["genres_title"],
        reply_markup=genres_keyboard(genres, back_callback="menu:back"),
    )

@router.callback_query(F.data.startswith("topg:"))
@inject
async def top_genre(callback: CallbackQuery, top_service: TopService = Provide[Container.top_service]):
    try:
        genre_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer()
        return

    texts = cfg["message"]["top"]

    if not top_service.chart_loaded(genre_id):
        await callback.answer(texts["updating"])
    else:
        await callback.answer()

    if not callback.message:
        return

    tracks = await top_service.get_chart(genre_id)

    if not tracks:
        await callback.message.edit_text(
            texts["empty"],
            reply_markup=tracks_keyboard(
                [], page=0, total=0,
                item_prefix=f"top:{genre_id}", page_prefix=f"tpage:{genre_id}",
                back_callback="menu:top", back_text=texts["buttons"]["back"],
            )
        )
        return

    chunk, total = top_service.page(genre_id, 0, PER_PAGE)

    await callback.message.edit_text(
        texts["chart_title"].format(genre=escape(top_service.genre_name(genre_id))),
        reply_markup=tracks_keyboard(
            chunk, page=0, total=total,
            item_prefix=f"top:{genre_id}", page_prefix=f"tpage:{genre_id}",
            back_callback="menu:top", back_text=texts["buttons"]["back"],
        )
    )

@router.callback_query(F.data.startswith("tpage:"))
@inject
async def top_page(callback: CallbackQuery, top_service: TopService = Provide[Container.top_service]):
    parts = callback.data.split(":")

    try:
        genre_id, page = int(parts[1]), int(parts[2])
    except (IndexError, ValueError):
        await callback.answer() # noop-кнопка счётчика или мусор
        return

    if not callback.message:
        return

    chunk, total = top_service.page(genre_id, page, PER_PAGE)

    if not chunk:
        return

    texts = cfg["message"]["top"]

    await callback.message.edit_text(
        texts["chart_title"].format(genre=escape(top_service.genre_name(genre_id))),
        reply_markup=tracks_keyboard(
            chunk, page=page, total=total,
            item_prefix=f"top:{genre_id}", page_prefix=f"tpage:{genre_id}",
            back_callback="menu:top", back_text=texts["buttons"]["back"],
        ),
    )

@router.callback_query(F.data.startswith("top:"))
@inject
async def top_track(
    callback: CallbackQuery,
    top_service: TopService = Provide[Container.top_service],
    downloader: DownloaderService = Provide[Container.downloader_service],
    file_cache: TrackFileCache = Provide[Container.file_cache],
):
    parts = callback.data.split(":")

    try:
        genre_id, source_id = int(parts[1]), int(parts[2])
    except (IndexError, ValueError):
        await callback.answer()
        return

    track = top_service.get_by_id(genre_id, source_id)

    if track is None:
        # Чарт жанра обновился, а у юзера на экране старый список
        with suppress(TelegramBadRequest):
            await callback.answer("Топ обновился — выбери жанр заново 🔝", show_alert=True)
        return

    await send_track_to_chat(callback, track, downloader, file_cache)