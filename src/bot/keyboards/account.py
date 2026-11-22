from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.configs.yaml_loader import cfg
from src.types.data.account import AccountData

def accounts_keyboard(
    accounts: list[AccountData],
    *,
    add_callback: str = "acc:add",
    back_callback: str = "menu:back",
) -> InlineKeyboardMarkup:
    buttons = cfg["message"]["accounts"]["buttons"]

    builder = InlineKeyboardBuilder()

    for account in accounts:
        builder.button(text=account.title, callback_data=f"acc:{account.id}")

    builder.button(text=buttons["add"], callback_data=add_callback)
    builder.button(text=buttons["back"], callback_data=back_callback)
    builder.adjust(*([1] * (len(accounts) + 2)))

    return builder.as_markup()

def profile_keyboard(account_id: int, *, back_callback: str = "menu:accounts") -> InlineKeyboardMarkup:
    buttons = cfg["message"]["accounts"]["buttons"]

    builder = InlineKeyboardBuilder()

    builder.button(text=buttons["audios"], callback_data=f"accaud:{account_id}")
    builder.button(text=buttons["playlists"], callback_data=f"accpl:{account_id}")
    builder.button(text=buttons["delete"], callback_data=f"accdel:{account_id}")
    builder.button(text=buttons["back"], callback_data=back_callback)
    builder.adjust(1, 1, 1, 1)

    return builder.as_markup()

def cancel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(
        text=cfg["message"]["accounts"]["buttons"]["cancel"],
        callback_data="acc:cancel",
    )

    builder.adjust(1)
    return builder.as_markup()