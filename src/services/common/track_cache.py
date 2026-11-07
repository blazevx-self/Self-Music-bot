from cachetools import TTLCache

from src.types.track import TrackData


class TrackFileCache:
    """
    Кэш file_id уже отправленных в Telegram аудиозаписей.

    Повторная отправка трека по file_id — мгновенно, без скачивания (yt-dlp)
    и без загрузки файла в Telegram. In-memory: maxsize — лимит записей, ttl — срок жизни.
    Для персистентности после рестарта бота — перенести в PostgreSQL (см. планы в README).
    """

    def __init__(self, maxsize: int = 500, ttl: int = 24 * 3600) -> None:
        self._cache: TTLCache = TTLCache(maxsize=maxsize, ttl=ttl)  # key -> file_id

    @staticmethod
    def key_for(track: TrackData) -> str:
        """Ключ кэша: Deezer id трека (есть и в поиске, и в новинках), иначе нормализованный «artist - title»."""
        if track.source_id:
            return f"deezer:{track.source_id}"
        return " ".join(f"{track.artist} - {track.title}".lower().split())

    def get(self, track: TrackData) -> str | None:
        return self._cache.get(self.key_for(track))

    def put(self, track: TrackData, file_id: str) -> None:
        self._cache[self.key_for(track)] = file_id

    def drop(self, track: TrackData) -> None:
        """Убрать запись (file_id устарел) — трек будет скачан заново."""
        self._cache.pop(self.key_for(track), None)
