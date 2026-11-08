from contextlib import suppress

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from dependency_injector.wiring import Provide, inject

from src.containers import Container
from src.configs.yaml_loader import cfg
from src.core.constants.pagination import PER_PAGE

from src.types.user_entity import UserData

from src.bot.keyboards.common.accounts import accounts_keyboard, cancel_keyboard, profile_keyboard
from src.bot.keyboards.common.tracks import tracks_keyboard
from src.bot.utils import send_track_to_chat

from src.services.common.accounts import AccountService
from src.services.common.downloader import DownloaderService
from src.services.common.track_cache import TrackFileCache
from src.services.external.deezer import DeezerClient

router = Router()


class AddAccount(StatesGroup):
    waiting_link = State()


def _texts() -> dict:
    return cfg["message"]["accounts"]


async def _edit_accounts(callback: CallbackQuery, user: UserData, account_service: AccountService) -> None:
    """Перерендер «Подключенных профилей» — общий хвост для menu:accounts / acc:cancel / accdel."""
    texts = _texts()
    accounts = await account_service.list_accounts(user)
    title = texts["title"] + (f"\n\n{texts['empty']}" if not accounts else "")

    if callback.message:
        await callback.message.edit_text(title, reply_markup=accounts_keyboard(accounts))


@router.callback_query(F.data == "menu:accounts")
@inject
async def open_accounts(
    callback: CallbackQuery,
    user: UserData,
    account_service: AccountService = Provide[Container.account_service],
):
    """Меню «Аккаунты»: список подключённых профилей («Добавить профиль» / «Назад»)."""
    await callback.answer()
    await _edit_accounts(callback, user, account_service)


@router.callback_query(F.data == "acc:add")
async def add_account_prompt(
    callback: CallbackQuery,
    state: FSMContext,
):
    """«Добавить профиль»: ждём ссылку (FSM), id сообщения-промпта сохраняем — потом удалим."""
    await state.set_state(AddAccount.waiting_link)

    if callback.message:
        await state.update_data(prompt_message_id=callback.message.message_id)

    await callback.answer()

    if callback.message:
        await callback.message.edit_text(_texts()["prompt"], reply_markup=cancel_keyboard())


@router.callback_query(F.data == "acc:cancel")
@inject
async def cancel_add(
    callback: CallbackQuery,
    user: UserData,
    state: FSMContext,
    account_service: AccountService = Provide[Container.account_service],
):
    """«Отмена»: сбрасываем состояние и редактируем сообщение обратно в список профилей."""
    await state.clear()
    await callback.answer()
    await _edit_accounts(callback, user, account_service)


@router.message(AddAccount.waiting_link, F.text)
@inject
async def handle_link(
    message: Message,
    user: UserData,
    state: FSMContext,
    bot: Bot,
    account_service: AccountService = Provide[Container.account_service],
):
    """
    Прислали ссылку в состоянии ожидания: парсим и сохраняем профиль.
    «invalid» — отвечаем подсказкой и остаёмся в состоянии; успех/лимит —
    чистим состояние, удаляем сообщение-промпт и шлём обновлённый список профилей.
    """
    texts = _texts()

    status, _account = await account_service.add_from_link(user, message.text or "")

    if status == "invalid":
        await message.answer(texts["invalid_link"])
        return

    await state.clear()

    data = await state.get_data()
    prompt_id = data.get("prompt_message_id")
    if prompt_id and message.chat:
        with suppress(TelegramBadRequest):
            await bot.delete_message(chat_id=message.chat.id, message_id=prompt_id)

    if status == "limit":
        await message.answer(texts["limit"])

    accounts = await account_service.list_accounts(user)
    await message.answer(texts["title"], reply_markup=accounts_keyboard(accounts))


@router.callback_query(F.data.startswith("accaud:"))
@inject
async def show_audios(
    callback: CallbackQuery,
    user: UserData,
    account_service: AccountService = Provide[Container.account_service],
):
    """«Аудиозаписи»: сначала проверка приватности — закрытый профиль даёт show_alert, иначе список треков."""
    try:
        account_id = int(callback.data.split(":", 1)[1])
    except (IndexError, ValueError):
        await callback.answer()
        return

    account = await account_service.get_owned(account_id, user)
    if account is None:
        await callback.answer(_texts()["not_found"], show_alert=True)
        return

    status, audios = await account_service.audios_status(account)

    if status != "ok":
        texts = _texts()
        alert = (
            texts["closed"] if status == "closed"
            else texts["empty_audios"] if status == "empty"
            else texts["unavailable"]
        )
        await callback.answer(alert, show_alert=True)
        return

    await callback.answer()

    if callback.message:
        await callback.message.edit_text(
            _texts()["audios_title"].format(title=account.title),
            reply_markup=tracks_keyboard(
                audios[:PER_PAGE], 0, len(audios),
                item_prefix=f"vka:{account.id}",
                page_prefix=f"vkap:{account.id}",
                back_callback=f"acc:{account.id}",
            ),
        )


@router.callback_query(F.data.startswith("vkap:"))
@inject
async def audios_page(
    callback: CallbackQuery,
    user: UserData,
    account_service: AccountService = Provide[Container.account_service],
):
    """Пагинация аудиозаписей: «vkap:<account_id>:<page>» (два int — парсим инлайн)."""
    try:
        account_id_s, page_s = callback.data.split(":", 1)[1].split(":")
        account_id, page = int(account_id_s), int(page_s)
    except (IndexError, ValueError):
        await callback.answer()  # сюда же прилетает «vkap:<id>:noop» — просто закрываем «часики»
        return

    account = await account_service.get_owned(account_id, user)
    if account is None:
        await callback.answer(_texts()["not_found"], show_alert=True)
        return

    status, audios = await account_service.audios_status(account)
    if status != "ok" or page < 0:
        await callback.answer()
        return

    await callback.answer()

    if callback.message:
        chunk = audios[page * PER_PAGE:(page + 1) * PER_PAGE]
        await callback.message.edit_text(
            _texts()["audios_title"].format(title=account.title),
            reply_markup=tracks_keyboard(
                chunk, page, len(audios),
                item_prefix=f"vka:{account.id}",
                page_prefix=f"vkap:{account.id}",
                back_callback=f"acc:{account.id}",
            ),
        )


@router.callback_query(F.data.startswith("vka:"))
@inject
async def play_vk_audio(
    callback: CallbackQuery,
    user: UserData,
    account_service: AccountService = Provide[Container.account_service],
    deezer: DeezerClient = Provide[Container.deezer_client],
    downloader: DownloaderService = Provide[Container.downloader_service],
    file_cache: TrackFileCache = Provide[Container.file_cache],
):
    """Клик по аудиозаписи «vka:<account_id>:<audio_id>»: ищем «artist - title» в Deezer и шлём трек как обычно."""
    try:
        account_id_s, audio_id_s = callback.data.split(":", 1)[1].split(":")
        account_id, audio_id = int(account_id_s), int(audio_id_s)
    except (IndexError, ValueError):
        await callback.answer()
        return

    audio = account_service.get_cached_audio(account_id, audio_id)
    if audio is None:
        await callback.answer(_texts()["cache_lost"], show_alert=True)
        return

    tracks = await deezer.search_tracks(f"{audio.artist} - {audio.title}", limit=5)
    if not tracks:
        await callback.answer(_texts()["not_in_deezer"], show_alert=True)
        return

    await send_track_to_chat(callback, tracks[0], downloader, file_cache)


@router.callback_query(F.data.startswith("accpl:"))
async def playlists_stub(callback: CallbackQuery):
    """«Плейлисты» профиля — пока заглушка (фича не делается сейчас)."""
    await callback.answer("🚧 Плейлисты пока в разработке", show_alert=True)


@router.callback_query(F.data.startswith("accdel:"))
@inject
async def delete_account(
    callback: CallbackQuery,
    user: UserData,
    account_service: AccountService = Provide[Container.account_service],
):
    """«Удалить»: удаляем профиль из БД и редактируем сообщение обратно в список профилей."""
    try:
        account_id = int(callback.data.split(":", 1)[1])
    except (IndexError, ValueError):
        await callback.answer()
        return

    deleted = await account_service.delete_owned(account_id, user)
    await callback.answer(_texts()["deleted"] if deleted else _texts()["not_found"])
    await _edit_accounts(callback, user, account_service)


@router.callback_query(F.data.startswith("acc:"))
@inject
async def open_profile(
    callback: CallbackQuery,
    user: UserData,
    account_service: AccountService = Provide[Container.account_service],
):
    """Клик по профилю: «Профиль: <название>» + «Аудиозаписи» / «Плейлисты» / «Удалить». Регистрируем ПОСЛЕ acc:add/acc:cancel."""
    try:
        account_id = int(callback.data.split(":", 1)[1])
    except (IndexError, ValueError):
        await callback.answer()
        return

    account = await account_service.get_owned(account_id, user)
    if account is None:
        await callback.answer(_texts()["not_found"], show_alert=True)
        return

    await callback.answer()

    if callback.message:
        await callback.message.edit_text(
            _texts()["profile_title"].format(title=account.title),
            reply_markup=profile_keyboard(account.id),
        )
