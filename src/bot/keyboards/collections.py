from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.configs.yaml_loader import cfg
from src.types.data.collections import CollectionData

def collections_keyboard(collections: list[CollectionData], back_callback: str | None = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for collection in collections:
        builder.button(text=collection.name, callback_data=f"mixg:{collection.id}")

    if back_callback:
        builder.button(text=cfg["message"]["mixes"]["buttons"]["back"], callback_data=back_callback)
        builder.adjust(*([1] * len(collections)), 1)
    else:
        builder.adjust(*([1] * len(collections)))

    return builder.as_markup()