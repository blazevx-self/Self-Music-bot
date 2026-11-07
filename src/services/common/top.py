import asyncio
from datetime import datetime, timedelta, timezone

from src.core.constants.pagination import PER_PAGE
from src.services.external.deezer import DeezerClient
from src.types.genre import GenreData
from src.types.track import TrackData
from src.utils.logger import system_logger


class TopService:
    """
    «Топ»: список жанров Deezer + топ треков каждого жанра по прослушиваниям.

    Кэши in-memory с TTL: жанры живут GENRES_TTL (они почти не меняются),
    чарт жанра — CHART_TTL. При ошибке сети возвращается последний успешный
    кэш (stale), а время свежести не обновляется — будет ретрай при следующем открытии.
    """

    GENRES_TTL = timedelta(days=7)
    # Deezer ранжирует чарт по rank (прослушивания) и обновляет его непрерывно:
    # трек с большим числом прослушиваний всплывает вверх сам. Поэтому чарт
    # освежаем каждый час (баланс актуальности и нагрузки на API), а не 12ч.
    # Если хочется «каждый заход свежий» — поставь timedelta(minutes=5).
    CHART_TTL = timedelta(hours=1)
    CHART_LIMIT = 70  # 70 треков = 7 страниц по 10, как на макете

    # Спец-жанр «Русский топ»: мировой чарт глобальный, RU-там почти нет,
    # поэтому для него — search по запросу + сортировка по rank (прослушивания)
    RUSSIAN_GENRE_ID = -1
    RUSSIAN_GENRE_NAME = "🇷🇺 Русский топ"
    RUSSIAN_QUERY = "русская музыка"  # поменяй на "phonk" / "русский рэп" и т.п. — что угодно

    def __init__(self, deezer: DeezerClient) -> None:
        self.deezer = deezer
        self._genres: list[GenreData] = []
        self._genres_at: datetime | None = None
        # genre_id -> (fetched_at, tracks, by_id)
        self._charts: dict[int, tuple[datetime, list[TrackData], dict[int, TrackData]]] = {}
        self._lock = asyncio.Lock()

    # ---------- жанры ----------

    @property
    def genres_loaded(self) -> bool:
        return bool(self._genres)

    def _genres_fresh(self) -> bool:
        return bool(
            self._genres
            and self._genres_at
            and datetime.now(timezone.utc) - self._genres_at < self.GENRES_TTL
        )

    def _all_genres(self) -> list[GenreData]:
        # спец-жанр «Русский топ» всегда первый в списке
        return [GenreData(id=self.RUSSIAN_GENRE_ID, name=self.RUSSIAN_GENRE_NAME)] + list(self._genres)

    async def get_genres(self) -> list[GenreData]:
        if self._genres_fresh():
            return self._all_genres()

        async with self._lock:
            if not self._genres_fresh():
                try:
                    genres = await self.deezer.genres()
                except Exception as e:
                    system_logger.error(f"[TOP] Genres fetch failed | error={e} | stale={len(self._genres)}")
                    genres = []

                if genres:
                    self._genres = genres
                    self._genres_at = datetime.now(timezone.utc)
                    system_logger.info(f"[TOP] Genres updated | count={len(genres)}")
                else:
                    system_logger.warning("[TOP] Genres fetch empty | stale kept")

        return self._all_genres()

    def genre_name(self, genre_id: int) -> str:
        if genre_id == self.RUSSIAN_GENRE_ID:
            return self.RUSSIAN_GENRE_NAME
        for genre in self._genres:
            if genre.id == genre_id:
                return genre.name
        return "Весь мир" if genre_id == 0 else str(genre_id)

    # ---------- чарты жанров ----------

    def chart_loaded(self, genre_id: int) -> bool:
        return genre_id in self._charts

    def _chart_fresh(self, genre_id: int) -> bool:
        entry = self._charts.get(genre_id)
        return bool(entry and datetime.now(timezone.utc) - entry[0] < self.CHART_TTL)

    async def get_chart(self, genre_id: int) -> list[TrackData]:
        """Топ треков жанра, при необходимости обновив кэш (stale-fallback при сбое)."""
        if self._chart_fresh(genre_id):
            return list(self._charts[genre_id][1])

        async with self._lock:
            if not self._chart_fresh(genre_id):
                try:
                    if genre_id == self.RUSSIAN_GENRE_ID:
                        # спец-жанр: топ по запросу, отсортированный по прослушиваниям (rank)
                        tracks = await self.deezer.top_by_query(self.RUSSIAN_QUERY, limit=self.CHART_LIMIT, min_year=2020)
                    else:
                        tracks = await self.deezer.genre_chart_tracks(genre_id, limit=self.CHART_LIMIT)
                except Exception as e:
                    system_logger.error(f"[TOP] Chart fetch failed | genre={genre_id} | error={e}")
                    tracks = []

                if tracks:  # пустой результат при сбое кэш НЕ затирает
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
        if not entry:
            return None
        return entry[2].get(source_id)

    def page(self, genre_id: int, page: int, per_page: int = PER_PAGE) -> tuple[list[TrackData], int]:
        entry = self._charts.get(genre_id)
        tracks = entry[1] if entry else []
        page = max(0, page)  # отрицательная page давала бы обратный срез
        start = page * per_page
        return tracks[start : start + per_page], len(tracks)
