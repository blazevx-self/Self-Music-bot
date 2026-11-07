from aiogram.types import InlineKeyboardMarkup

# Импорт PER_PAGE здесь же реэкспортирует его: роутер делает
# `from src.bot.keyboards.common.search import PER_PAGE, search_keyboard`
# (отдельная строка `PER_PAGE = PER_PAGE` не нужна — это self-assignment)
from src.core.constants.pagination import PER_PAGE
from src.types.track import TrackData
from src.bot.keyboards.common.tracks import tracks_keyboard


def search_keyboard(tracks: list[TrackData], page: int, total: int) -> InlineKeyboardMarkup:
    """
    Клавиатура результатов поиска — тонкая обёртка над tracks_keyboard.
    ВАЖНО: page_prefix="spage" (не "stage"!) — на него слушает роутер spage:*.
    """
    return tracks_keyboard(tracks, page, total, item_prefix="srch", page_prefix="spage")
