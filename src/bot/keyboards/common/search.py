from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.types.track import TrackData

PER_PAGE = 10

def _duration(sec: int) -> str:
    minutes, seconds = divmod(int(sec), 60)
    return f"{minutes}:{seconds:02d}"

def search_keyboard(
    tracks: list[TrackData],
    page: int,
    total: int,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for track in tracks:
        label = f"{_duration(track.duration_sec)} {track.artist} - {track.title}"

        if len(label) > 60:
            label = label[:57] + "..."

        builder.button(text=label, callback_data=f"srch:{track.source_id}")

    pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)

    if page > 0:
        builder.button(text="<<", callback_data=f"spage:{page - 1}")

    builder.button(text=f"{page + 1} / {pages}", callback_data="spage:noop")

    if page + 1 < pages:
        builder.button(text=">>", callback_data=f"spage:{page + 1}")

    nav = 1 + int(page > 0) + int(page + 1 < pages)
    builder.adjust(*([1] * len(tracks)), nav)

    return builder.as_markup()