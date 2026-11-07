from aiogram.types import InlineKeyboardMarkup

from src.core.constants.pagination import PER_PAGE
from src.types.data.track import TrackData

from src.bot.keyboards.common.tracks import tracks_keyboard

def search_keyboard(tracks: list[TrackData], page: int, total: int) -> InlineKeyboardMarkup:
    return tracks_keyboard(tracks, page, total, item_prefix="srch", page_prefix="spage")