import asyncio
from datetime import datetime, timedelta, timezone

from src.core.constants.pagination import PER_PAGE
from src.types.track import TrackData

from src.services.external.deezer import DeezerClient
from src.utils.logger import system_logger

class NewReleasesService:
    """
        «Новинки мира»: мировой чарт треков Deezer с кэшем в памяти процесса.

        Кэш обновляется лениво при get_tracks(), не чаще раза в REFRESH_INTERVAL,
        поэтому каждый день состав разный. При ошибке сети возвращается последний
        успешный кэш (stale), а _fetched_at НЕ обновляется — ретmouth на следующем открытии.
        """

    REFRESH_INTERVAL = timedelta(hours=12)
    CHART_LIMIT = 70

    def __init__(self, deezer: DeezerClient) -> None:
        self.deezer = deezer
        self._tracks: list[TrackData] = []
        self._by_id: dict[int, TrackData] = {}
        self._fetched_at: datetime | None = None
        self._lock = asyncio.Lock()

    def _is_fresh(self) -> bool:
        return bool(
            self._tracks
            and self._fetched_at
            and datetime.now(timezone.utc) - self._fetched_at < self.REFRESH_INTERVAL
        )

    @property
    def is_loaded(self) -> bool:
        return bool(self._tracks)

    async def _fetch_and_store(self) -> None:
        try:
            tracks = await self.deezer.world_chart_tracks(limit=self.CHART_LIMIT)
        except Exception as e:
            system_logger.error(
                f"[NEW] Chart fetch failed | error={e} | stale_tracks={len(self._tracks)}"
            )
            return

        if not tracks:
            system_logger.warning("[NEW] Chart fetch returned empty | stale cache kept")
            return

        self._tracks = tracks
        self._by_id = {t.source_id: t for t in tracks}
        self._fetched_at = datetime.now(timezone.utc)

        system_logger.info(f"[NEW] Chart updated | tracks={len(tracks)}")

    async def get_tracks(self) -> list[TrackData]:
        """Вернуть актуальный список новинок, при необходимости обновив кэш."""
        if self._is_fresh():
            return list(self._tracks)

        async with self._lock:
            if not self._is_fresh():
                await self._fetch_and_store()

        return list(self._tracks)

    async def refresh(self) -> None: # ADD (опционально): prewarm при старте бота
        async with self._lock:
            await self._fetch_and_store()

    def get_by_id(self, source_id: int) -> TrackData | None:
        return self._by_id.get(source_id)

    def page(self, page: int, per_page: int = PER_PAGE) -> tuple[list[TrackData], int]:
        page = max(0, page)
        start = page * per_page
        chunk = self._tracks[start : start + per_page]
        return chunk, len(self._tracks)