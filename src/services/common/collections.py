import asyncio
from datetime import datetime, timedelta, timezone

from src.core.constants.pagination import PER_PAGE
from src.services.external.deezer import DeezerClient
from src.types.collection import CollectionData
from src.types.track import TrackData
from src.utils.logger import system_logger


class CollectionService:
    """
    «Подборки»: статический список подборок по настроениям; каждая подборка —
    топ по поисковому запросу (DeezerClient.top_by_query: /search + сортировка
    по rank, т.е. по прослушиваниям).

    Кэш подборок in-memory с TTL, как у TopService: при сбое сети возвращается
    последний успешный кэш (stale), время свежести не обновляется — ретрай при
    следующем открытии.
    """

    COLLECTION_TTL = timedelta(hours=1)
    COLLECTION_LIMIT = 100  # /search отдаёт максимум 100 → 10 страниц по 10

    # RU-подборки первые: мировой чарт глобальный, русского там почти нет.
    # min_year — фильтр по году выпуска альбома (rank — всевременной, потому
    # без фильтра в топе всплывает старьё).
    COLLECTIONS: tuple[CollectionData, ...] = (
        CollectionData(0, "🇷🇺 Русский топ", "русская музыка", min_year=2020),
        CollectionData(11, "🎤 Русский реп", "русский реп", min_year=2023),
        CollectionData(12, "👻 Русский phonk", "русский phonk", min_year=2023),
        CollectionData(1, "🚗 В дорогу", "музыка в дороге", min_year=2024),
        CollectionData(2, "🎉 Вечеринка", "party music", min_year=2024),
        CollectionData(3, "😢 Грустная", "грустные песни", min_year=2024),
        CollectionData(4, "⚡ Заряд энергии", "энергичная музыка", min_year=2024),
        CollectionData(5, "🎯 Концентрация", "музыка для концентрации", min_year=2024),
        CollectionData(6, "🌴 Отдых", "chill музыка для отдыха", min_year=2024),
        CollectionData(7, "💕 Романтика", "романтическая музыка", min_year=2024),
        CollectionData(8, "😴 Сон", "музыка для сна", min_year=2024),
        CollectionData(9, "💪 Тренировка", "музыка для тренировки", min_year=2024),
        CollectionData(10, "😊 Хорошее настроение", "весёлая музыка", min_year=2024),
    )

    def __init__(self, deezer: DeezerClient) -> None:
        self.deezer = deezer
        # coll_id -> (fetched_at, tracks, by_id)
        self._cache: dict[int, tuple[datetime, list[TrackData], dict[int, TrackData]]] = {}
        self._lock = asyncio.Lock()

    def get_collections(self) -> list[CollectionData]:
        # список статический — сеть не нужна
        return list(self.COLLECTIONS)

    def collection_name(self, coll_id: int) -> str:
        for c in self.COLLECTIONS:
            if c.id == coll_id:
                return c.name
        return str(coll_id)

    def _collection(self, coll_id: int) -> CollectionData | None:
        for c in self.COLLECTIONS:
            if c.id == coll_id:
                return c
        return None

    def collection_loaded(self, coll_id: int) -> bool:
        return coll_id in self._cache

    def _fresh(self, coll_id: int) -> bool:
        entry = self._cache.get(coll_id)
        return bool(entry and datetime.now(timezone.utc) - entry[0] < self.COLLECTION_TTL)

    async def get_collection(self, coll_id: int) -> list[TrackData]:
        """Топ треков подборки, при необходимости обновив кэш (stale-fallback при сбое)."""
        if self._fresh(coll_id):
            return list(self._cache[coll_id][1])

        collection = self._collection(coll_id)

        async with self._lock:
            if not self._fresh(coll_id) and collection:
                try:
                    tracks = await self.deezer.top_by_query(
                        collection.query, limit=self.COLLECTION_LIMIT, min_year=collection.min_year
                    )
                except Exception as e:
                    system_logger.error(f"[MIXES] Fetch failed | coll={coll_id} | error={e}")
                    tracks = []

                if tracks:  # пустой результат при сбое кэш НЕ затирает
                    self._cache[coll_id] = (
                        datetime.now(timezone.utc),
                        tracks,
                        {t.source_id: t for t in tracks},
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
        page = max(0, page)  # отрицательная page давала бы обратный срез
        start = page * per_page
        return tracks[start : start + per_page], len(tracks)
