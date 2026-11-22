from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.configs.yaml_loader import cfg

def settings_keyboard(flags: dict[str, bool], back_callback: str | None = None) -> InlineKeyboardMarkup:
    texts = cfg["message"]["settings"]
    builder = InlineKeyboardBuilder()

    for key, enabled in flags.items():
        label = texts["buttons"].get(key, key)
        state = texts["enabled"] if enabled else texts["disabled"]

        builder.button(text=f"{label}: {state}", callback_data=f"set:{key}")

    if back_callback:
        builder.button(text=texts["buttons"]["back"], callback_data=back_callback)
        builder.adjust(*([1] * len(flags)), 1)
    else:
        builder.adjust(*([1] * len(flags)))

    return builder.as_markup()