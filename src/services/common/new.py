import asyncio
from datetime import datetime, timedelta, timezone

from src.core.constants.pagination import PER_PAGE
from src.services.external.deezer import DeezerClient
from src.types.track import TrackData
from src.utils.logger import system_logger


class NewReleasesService:
    """
    «Новинки мира»: мировой чарт треков Deezer (/chart/0/tracks) с кэшем в памяти процесса.

    Кэш обновляется лениво при get_tracks() не чаще раза в REFRESH_INTERVAL,
    поэтому каждый день состав разный. При ошибке сети возвращается последний
    успешный кэш (stale), а _fetched_at НЕ обновляется — будет ретрай при следующем открытии.
    """

    REFRESH_INTERVAL = timedelta(hours=12)  # сколько живёт кэш
    CHART_LIMIT = 70                        # 70 треков = 7 страниц по 10, как на макете

    def __init__(self, deezer: DeezerClient) -> None:
        self.deezer = deezer
        self._tracks: list[TrackData] = []
        self._by_id: dict[int, TrackData] = {}
        self._fetched_at: datetime | None = None
        self._lock = asyncio.Lock()  # ок на Python 3.10+: loop не нужен при создании

    def _is_fresh(self) -> bool:
        return bool(
            self._tracks
            and self._fetched_at
            and datetime.now(timezone.utc) - self._fetched_at < self.REFRESH_INTERVAL
        )

    @property
    def is_loaded(self) -> bool:
        """True, если в кэше уже есть список (роутер использует для текста «Обновляю…»)."""
        return bool(self._tracks)

    async def _fetch_and_store(self) -> None:
        """
        Скачать чарт и обновить кэш. Вызывать только под self._lock.

        Важно: кэш обновляется ТОЛЬКО при непустом результате — world_chart_tracks()
        при сбое возвращает [], и перезапись кэша пустым списком уничтожила бы
        хорошие «новинки» на следующие REFRESH_INTERVAL часов.
        """
        try:
            tracks = await self.deezer.world_chart_tracks(limit=self.CHART_LIMIT)
        except Exception as e:
            system_logger.error(
                f"[NEW] Chart fetch failed | error={e} | stale_tracks={len(self._tracks)}"
            )
            return  # старый кэш и старый _fetched_at остаются

        if not tracks:
            system_logger.warning("[NEW] Chart fetch returned empty | stale cache kept")
            return

        # Между присваиваниями нет await — для читателей в asyncio это атомарно
        self._tracks = tracks
        self._by_id = {t.source_id: t for t in tracks}
        self._fetched_at = datetime.now(timezone.utc)
        system_logger.info(f"[NEW] Chart updated | tracks={len(tracks)}")

    async def get_tracks(self) -> list[TrackData]:
        """Вернуть актуальный список новинок, при необходимости обновив кэш (stale-fallback при сбое)."""
        if self._is_fresh():
            return list(self._tracks)  # копия, а не живая ссылка

        async with self._lock:
            if not self._is_fresh():   # double-checked locking: другой запрос мог уже обновить
                await self._fetch_and_store()

        return list(self._tracks)

    async def refresh(self) -> None:
        """Принудительно обновить кэш (например, prewarm при старте бота)."""
        async with self._lock:
            await self._fetch_and_store()

    def get_by_id(self, source_id: int) -> TrackData | None:
        return self._by_id.get(source_id)

    def page(self, page: int, per_page: int = PER_PAGE) -> tuple[list[TrackData], int]:
        page = max(0, page)  # отрицательная page давала бы обратный срез (tracks[-20:-10])
        start = page * per_page
        chunk = self._tracks[start : start + per_page]
        return chunk, len(self._tracks)
