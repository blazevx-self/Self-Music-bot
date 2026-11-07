from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.core.constants.pagination import PER_PAGE
from src.types.track import TrackData


def _duration(sec: int) -> str:
    minutes, seconds = divmod(int(sec), 60)
    return f"{minutes}:{seconds:02d}"


def tracks_keyboard(
    tracks: list[TrackData],
    page: int,
    total: int,
    *,
    item_prefix: str,                    # "srch" (поиск) / "new" (новинки) — клик по треку: "<prefix>:<source_id>"
    page_prefix: str,                    # "spage" / "npage" — пагинация: "<prefix>:<page>"
    back_callback: str | None = None,    # например "menu:back" — кнопка «Назад» отдельной строкой внизу
    back_text: str | None = None,
    per_page: int = PER_PAGE,
) -> InlineKeyboardMarkup:
    """
    Универсальная клавиатура списка треков (поиск и новинки):
    по одной кнопке на трек, строка пагинации «<<  1 / 7  >>»
    и опциональная кнопка «Назад» внизу.
    """
    builder = InlineKeyboardBuilder()

    for track in tracks:
        label = f"{_duration(track.duration_sec)} {track.artist} - {track.title}"

        if len(label) > 60:
            label = label[:57] + "..."

        builder.button(text=label, callback_data=f"{item_prefix}:{track.source_id}")

    pages = max(1, (total + per_page - 1) // per_page)

    if page > 0:
        builder.button(text="<<", callback_data=f"{page_prefix}:{page - 1}")

    builder.button(text=f"{page + 1} / {pages}", callback_data=f"{page_prefix}:noop")

    if page + 1 < pages:
        builder.button(text=">>", callback_data=f"{page_prefix}:{page + 1}")

    nav = 1 + int(page > 0) + int(page + 1 < pages)

    if back_callback:
        builder.button(text=back_text or "Назад", callback_data=back_callback)
        builder.adjust(*([1] * len(tracks)), nav, 1)
    else:
        builder.adjust(*([1] * len(tracks)), nav)

    return builder.as_markup()
