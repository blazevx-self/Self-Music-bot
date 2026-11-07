from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.configs.yaml_loader import cfg
from src.types.data.genre import GenreData

def genres_keyboard(genres: list[GenreData], back_callback: str | None = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for genre in genres:
        builder.button(text=genre.name, callback_data=f"topg:{genre.id}")

    rows = [2] * ((len(genres) + 1) // 2)

    if back_callback:
        builder.button(
            text=cfg["message"]["top"]["buttons"]["back"],
            callback_data=back_callback,
        )
        builder.adjust(*rows, 1)
    else:
        builder.adjust(*rows)

    return builder.as_markup()