from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.filters import Command

from dependency_injector.wiring import Provide, inject

from src.containers import Container
from src.configs.yaml_loader import cfg

from src.types.data.user import UserData

from src.services.common.settings import SettingsService
from src.bot.keyboards.common.settings import settings_keyboard

router = Router()

def _settings_view(
    user: UserData,
    settings_service: SettingsService,
) -> tuple[str, InlineKeyboardMarkup]:
    texts = cfg["message"]["settings"]
    keyboard = settings_keyboard(
        settings_service.flags(user),
        back_callback="menu:back"
    )
    return texts["title"], keyboard

@router.message(Command("settings"))
@inject
async def settings_cmd(
    message: Message,
    user: UserData,
    settings_service: SettingsService = Provide[Container.settings_service]
):
    text, keyboard = _settings_view(user, settings_service)
    await message.answer(text, reply_markup=keyboard)

@router.callback_query(F.data == "menu:settings")
@inject
async def open_settings(
    callback: CallbackQuery,
    user: UserData,
    settings_service: SettingsService = Provide[Container.settings_service],
):
    await callback.answer()

    if not callback.message:
        return

    text, keyboard = _settings_view(user, settings_service)
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("set:"))
@inject
async def toggle_setting(
    callback: CallbackQuery,
    user: UserData,
    settings_service: SettingsService = Provide[Container.settings_service],
):
    key = callback.data.split(":", 1)[1]
    texts = cfg["message"]["settings"]

    if key not in settings_service.FLAGS:
        await callback.answer(texts["unknown"], show_alert=True)
        return

    new_value = await settings_service.toggle(user, key)

    if new_value is None:
        await callback.answer()
        return

    await callback.answer(texts["enabled"] if new_value else texts["disabled"])

    if not callback.message:
        return

    flags = settings_service.flags(user)
    flags[key] = new_value

    await callback.message.edit_text(
        texts["title"],
        reply_markup=settings_keyboard(flags, back_callback="menu:back")
    )