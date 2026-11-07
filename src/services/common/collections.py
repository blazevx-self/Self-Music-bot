import asyncio
from datetime import datetime, timedelta, timezone

from src.core.constants.pagination import PER_PAGE

from src.types.data.collections import CollectionData
from src.types.data.track import TrackData

from src.services.external.deezer import DeezerClient
from src.utils.logger import system_logger


class CollectionService:
    """«Подборки»: статический список + топ по запросу (top_by_query). Кэш с TTL, stale при сбое."""

    COLLECTION_TTL = timedelta(hours=1)
    COLLECTION_LIMIT = 100

    COLLECTIONS: tuple[CollectionData, ...] = (
        CollectionData(1, "В дорогу", "музыка в дороге"),
        CollectionData(2, "Вечеринка", "party music 2026"),
        CollectionData(3, "Грустная", "грустные песни"),
        CollectionData(4, "Заряд энергии", "энергичная музыка"),
        CollectionData(5, "Концентрация", "музыка для концентрации"),
        CollectionData(6, "Отдых", "chill музыка для отдыха"),
        CollectionData(7, "Романтика", "романтическая музыка"),
        CollectionData(8, "Сон", "музыка для сна"),
        CollectionData(9, "Тренировка", "музыка для тренировки"),
        CollectionData(10, "Хорошее настроение", "весёлая музыка"),
    )

    def __init__(self, deezer: DeezerClient) -> None:
        self.deezer = deezer
        self._cache: dict[int, tuple[datetime, list[TrackData], dict[int, TrackData]]] = {}
        self._lock = asyncio.Lock()

    def get_collections(self) -> list[CollectionData]:
        return list(self.COLLECTIONS)

    def collection_name(self, coll_id: int) -> str:
        for c in self.COLLECTIONS:
            if c.id == coll_id:
                return c.name

        return str(coll_id)

    def _query(self, coll_id: int) -> str | None:
        # то же самое, что collection_name, но вернуть .query; если не нашли — return None
        for c in self.COLLECTIONS:
            if c.id == coll_id:
                return c.query

        return None

    def collection_loaded(self, coll_id: int) -> bool:
        return coll_id in self._cache

    def _fresh(self, coll_id: int) -> bool:
        entry = self._cache.get(coll_id)
        return bool(entry and datetime.now(timezone.utc) - entry[0] < self.COLLECTION_TTL)

    async def get_collection(self, coll_id: int) -> list[TrackData]:
        if self._fresh(coll_id):
            return list(self._cache[coll_id][1])

        query = self._query(coll_id)

        async with self._lock:
            if not self._fresh(coll_id) and query:
                try:
                    tracks = await self.deezer.search_tracks(query, limit=self.COLLECTION_LIMIT)
                except Exception as e:
                    system_logger.error(f"[MIXES] Fetch failed | coll={coll_id} | error={e}")
                    tracks = []

                if tracks:  # пустой результат при сбое кэш НЕ затирает
                    self._cache[coll_id] = (
                        datetime.now(timezone.utc),
                        tracks,
                        {t.source_id: t for t in tracks}
                    )
                    system_logger.info(f"[MIXES] Collection updated | coll={coll_id} | tracks={len(tracks)}")
                else:
                    system_logger.warning(f"[MIXES] Collection empty | coll={coll_id} | stale kept")

        entry = self._cache.get(coll_id)
        return list(entry[1]) if entry else []

    def get_by_id(self, coll_id: int, source_id: int) -> TrackData | None:
        entry = self._cache.get(coll_id)

        if not entry:
            return None

        return entry[2].get(source_id)

    def page(self, coll_id: int, page: int, per_page: int = PER_PAGE) -> tuple[list[TrackData], int]:
        entry = self._cache.get(coll_id)
        tracks = entry[1] if entry else []
        page = max(0, page) # отрицательная page давала бы обратный срез
        start = page * per_page
        return tracks[start : start + per_page], len(tracks)