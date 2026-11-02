from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.configs.settings import settings
from src.configs.yaml_loader import cfg

def subscribe_keyboard() -> InlineKeyboardMarkup:
    buttons = cfg["message"]["start"]["buttons"]

    builder = InlineKeyboardBuilder()

    builder.button(text=buttons["subscribe"], url=settings.CHANNEL_URL)
    builder.button(text=buttons["check"], callback_data="sub:check")

    builder.adjust(1)

    return builder.as_markup()

def menu_keyboard() -> InlineKeyboardMarkup:
    buttons = cfg["message"]["start"]["buttons"]

    builder = InlineKeyboardBuilder()

    builder.button(text=buttons["new"], callback_data="menu:new")
    builder.button(text=buttons["help"], callback_data="menu:help")
    builder.button(text=buttons["top"], callback_data="menu:top")
    builder.button(text=buttons["mixes"], callback_data="menu:mixes")
    builder.button(text=buttons["playlists"], callback_data="menu:playlists")
    builder.button(text=buttons["accounts"], callback_data="menu:accounts")
    builder.button(text=buttons["settings"], callback_data="menu:settings")

    builder.adjust(3, 2, 2)

    return builder.as_markup()

def back_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(
       text=cfg["message"]["help"]["buttons"]["back"],
        callback_data="menu:back",
    )

    return builder.as_markup()