from html import escape
from contextlib import suppress

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery

from dependency_injector.wiring import Provide, inject

from src.containers import Container
from src.configs.yaml_loader import cfg
from src.core.constants.pagination import PER_PAGE

from src.bot.keyboards.common.tracks import tracks_keyboard
from src.bot.keyboards.common.collections import collections_keyboard
from src.bot.utils import send_track_to_chat

from src.services.common.collections import CollectionService
from src.services.common.downloader import DownloaderService
from src.services.common.track_cache import TrackFileCache

router = Router()


@router.callback_query(F.data == "menu:mixes")
@inject
async def open_mixes(
    callback: CallbackQuery,
    collection_service: CollectionService = Provide[Container.collection_service],
):
    """Пункт меню «Подборки»: статический список подборок («Назад» — в главное меню)."""
    texts = cfg["message"]["mixes"]

    await callback.answer()

    if not callback.message:
        return

    await callback.message.edit_text(
        texts["title"],
        reply_markup=collections_keyboard(
            collection_service.get_collections(), back_callback="menu:back"
        ),
    )


@router.callback_query(F.data.startswith("mixg:"))
@inject
async def mix_collection(
    callback: CallbackQuery,
    collection_service: CollectionService = Provide[Container.collection_service],
):
    """Выбор подборки: первая страница треков подборки (топ по запросу подборки)."""
    try:
        coll_id = int(callback.data.split(":")[1])  # mixg:<coll_id>
    except (IndexError, ValueError):
        await callback.answer()
        return

    texts = cfg["message"]["mixes"]

    if not collection_service.collection_loaded(coll_id):
        await callback.answer(texts["updating"])
    else:
        await callback.answer()

    if not callback.message:
        return

    tracks = await collection_service.get_collection(coll_id)

    if not tracks:
        await callback.message.edit_text(
            texts["empty"],
            reply_markup=tracks_keyboard(
                [], page=0, total=0,
                item_prefix=f"mix:{coll_id}", page_prefix=f"mpage:{coll_id}",
                back_callback="menu:mixes", back_text=texts["buttons"]["back"],
            ),
        )
        return

    chunk, total = collection_service.page(coll_id, 0, PER_PAGE)

    await callback.message.edit_text(
        texts["collection_title"].format(collection=escape(collection_service.collection_name(coll_id))),
        reply_markup=tracks_keyboard(
            chunk, page=0, total=total,
            item_prefix=f"mix:{coll_id}", page_prefix=f"mpage:{coll_id}",
            back_callback="menu:mixes", back_text=texts["buttons"]["back"],
        ),
    )


@router.callback_query(F.data.startswith("mpage:"))
@inject
async def mix_page(
    callback: CallbackQuery,
    collection_service: CollectionService = Provide[Container.collection_service],
):
    """Пагинация подборки: «mpage:<coll_id>:<page>»; «mpage:<coll_id>:noop» — просто answer."""
    parts = callback.data.split(":")

    try:
        coll_id, page = int(parts[1]), int(parts[2])
    except (IndexError, ValueError):
        await callback.answer()  # noop-кнопка счётчика или мусор
        return

    await callback.answer()

    if not callback.message:
        return

    chunk, total = collection_service.page(coll_id, page, PER_PAGE)

    if not chunk:
        return

    texts = cfg["message"]["mixes"]

    await callback.message.edit_text(
        texts["collection_title"].format(collection=escape(collection_service.collection_name(coll_id))),
        reply_markup=tracks_keyboard(
            chunk, page=page, total=total,
            item_prefix=f"mix:{coll_id}", page_prefix=f"mpage:{coll_id}",
            back_callback="menu:mixes", back_text=texts["buttons"]["back"],
        ),
    )


@router.callback_query(F.data.startswith("mix:"))
@inject
async def mix_track(
    callback: CallbackQuery,
    collection_service: CollectionService = Provide[Container.collection_service],
    downloader: DownloaderService = Provide[Container.downloader_service],
    file_cache: TrackFileCache = Provide[Container.file_cache],
):
    """Клик по треку подборки: «mix:<coll_id>:<source_id>» — file_id-кэш → yt-dlp → аудио в чат."""
    parts = callback.data.split(":")

    try:
        coll_id, source_id = int(parts[1]), int(parts[2])
    except (IndexError, ValueError):
        await callback.answer()
        return

    track = collection_service.get_by_id(coll_id, source_id)

    if track is None:
        # Подборка обновилась, а у юзера на экране старый список
        with suppress(TelegramBadRequest):
            await callback.answer("Подборка обновилась — выбери её заново 🎧", show_alert=True)
        return  # return за пределами with

    await send_track_to_chat(callback, track, downloader, file_cache)
