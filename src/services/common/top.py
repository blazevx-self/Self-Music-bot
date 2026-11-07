import asyncio
from datetime import datetime, timedelta, timezone

from src.core.constants.pagination import PER_PAGE

from src.types.data.genre import GenreData
from src.types.data.track import TrackData

from src.services.external.deezer import DeezerClient
from src.utils.logger import system_logger

class TopService:
    GENRES_TTL = timedelta(days=7)
    CHART_TTL = timedelta(hours=1)
    CHART_LIMIT = 70

    def __init__(self, deezer: DeezerClient) -> None:
        self.deezer = deezer
        self._genres: list[GenreData] = []
        self._genres_at: datetime | None = None
        self._charts: dict[int, tuple[datetime, list[TrackData], dict[int, TrackData]]] = {}
        self._lock = asyncio.Lock()

    @property
    def genres_loaded(self) -> bool:
        return bool(self._genres)

    def chart_loaded(self, genre_id: int) -> bool:
        return genre_id in self._charts

    async def get_genres(self) -> list[GenreData]:
        now = datetime.now(timezone.utc)

        if self._genres and self._genres_at is not None and now - self._genres_at < self.GENRES_TTL:
            return list(self._genres)

        async with self._lock:
            now = datetime.now(timezone.utc)

            if self._genres and self._genres_at is not None and now - self._genres_at < self.GENRES_TTL:
                return list(self._genres)

            try:
                genres = await self.deezer.genres()
            except Exception as e:
                system_logger.error(f"[TOP] Genres fetch failed | error={e} | stale={len(self._genres)}")
                genres = []

            if genres:
                self._genres = genres
                self._genres_at = now
            elif self._genres:
                system_logger.warning("[TOP] Genres empty | stale kept")

        return list(self._genres)

    def genre_name(self, genre_id: int) -> str:
        if genre_id == 0:
            return "Весь мир"

        for genre in self._genres:
            if genre.id == genre_id:
                return genre.name

        return str(genre_id)

    async def get_chart(self, genre_id: int) -> list[TrackData]:
        entry = self._charts.get(genre_id)

        if entry and datetime.now(timezone.utc) - entry[0] < self.CHART_TTL:
            return list(entry[1])

        async with self._lock:
            entry = self._charts.get(genre_id)

            if entry and datetime.now(timezone.utc) - entry[0] < self.CHART_TTL:
                return list(entry[1])

            try:
                tracks = await self.deezer.genre_chart_tracks(genre_id, limit=self.CHART_LIMIT)
            except Exception as e:
                system_logger.error(f"[TOP] Chart fetch failed | genre={genre_id} | error={e}")
                tracks = []

            if tracks:
                self._charts[genre_id] = (
                    datetime.now(timezone.utc),
                    tracks,
                    {t.source_id: t for t in tracks},
                )
                system_logger.info(f"[TOP] Chart updated | genre={genre_id} | tracks={len(tracks)}")
            else:
                system_logger.warning(f"[TOP] Chart empty | genre={genre_id} | stale kept")

        entry = self._charts.get(genre_id)
        return list(entry[1]) if entry else []

    def get_by_id(self, genre_id: int, source_id: int) -> TrackData | None:
        entry = self._charts.get(genre_id)

        if entry is None:
            return None

        return entry[2].get(source_id)

    def page(self, genre_id: int, page: int, per_page: int = PER_PAGE):
        entry = self._charts.get(genre_id)
        tracks = entry[1] if entry else []
        page = max(0, page)
        start = page * per_page
        return tracks[start : start + per_page], len(tracks)