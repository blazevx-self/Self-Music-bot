import aiohttp

from src.types.genre import GenreData
from src.types.track import TrackData
from src.utils.logger import system_logger

DEEZER_BASE_URL = "https://api.deezer.com"


def _to_track(item: dict) -> TrackData | None:
    """
    Парсер элемента Deezer в TrackData.

    Работает и для /search, и для /chart/0/tracks — форма объекта одинаковая
    (id, title, duration, preview, artist.name, album.cover_medium).
    """
    preview = item.get("preview") or ""

    if not preview:
        return None

    artist = (item.get("artist") or {}).get("name") or ""
    cover = (item.get("album") or {}).get("cover_medium")

    return TrackData(
        source_id=item["id"],
        title=item.get("title") or "",
        artist=artist,
        duration_sec=item.get("duration") or 0,
        preview_url=preview,
        cover_url=cover,
        rank=item.get("rank") or 0,
    )


class DeezerClient:
    """Единая точка доступа к публичному API Deezer (ключ не требуется)."""

    def __init__(self, timeout_sec: float = 10.0) -> None:
        self._timeout = aiohttp.ClientTimeout(total=timeout_sec)

    async def _get_json(self, path: str, params: dict) -> dict | None:
        """
        GET к API Deezer с таймаутом и единой обработкой ошибок.

        :return: Распарсенный JSON либо None при любой ошибке (сеть, статус, не-JSON).
        """
        try:
            async with aiohttp.ClientSession(timeout=self._timeout) as session:
                async with session.get(DEEZER_BASE_URL + path, params=params) as response:
                    if response.status != 200:
                        system_logger.warning(
                            f"[DEEZER] HTTP {response.status} | path={path} | params={params}"
                        )
                        return None

                    return await response.json()
        except (aiohttp.ClientError, ValueError) as e:
            system_logger.warning(f"[DEEZER] Request failed | path={path} | error={e}")
            return None

    @staticmethod
    def _parse_tracks(payload: dict | None) -> list[TrackData]:
        """Свернуть payload формата {"data": [...]} в список TrackData, пропуская битые элементы."""
        if not payload:
            return []

        items = payload.get("data") or []

        if not isinstance(items, list):
            return []

        tracks: list[TrackData] = []

        for item in items:
            if not isinstance(item, dict):
                continue

            track = _to_track(item)

            if track is not None:
                tracks.append(track)

        return tracks

    async def search_tracks(self, query: str, limit: int = 25) -> list[TrackData]:
        """Поиск треков по запросу через /search."""
        query = query.strip()

        if not query:
            return []

        payload = await self._get_json("/search", {"q": query, "limit": limit})
        return self._parse_tracks(payload)

    async def world_chart_tracks(self, limit: int = 70) -> list[TrackData]:
        """Мировой чарт треков через /chart/0/tracks — источник для раздела «Новинки»."""
        payload = await self._get_json("/chart/0/tracks", {"limit": limit})
        return self._parse_tracks(payload)

    async def genre_chart_tracks(self, genre_id: int, limit: int = 70) -> list[TrackData]:
        """
        Топ треков жанра по прослушиваниям (/chart/{genre_id}/tracks).
        genre_id=0 — мировой топ. Источник для раздела «Топ».
        """
        payload = await self._get_json(f"/chart/{genre_id}/tracks", {"limit": limit})
        return self._parse_tracks(payload)

    async def top_by_query(self, query: str, limit: int = 70) -> list[TrackData]:
        """
        «Топ по запросу»: /search + сортировка по rank (прослушивания) по убыванию.
        Используется для спец-жанра «Русский топ» — мировой чарт глобальный и RU-там почти нет.
        """
        payload = await self._get_json("/search", {"q": query, "limit": 100})
        tracks = self._parse_tracks(payload)
        tracks.sort(key=lambda t: t.rank, reverse=True)
        return tracks[:limit]

    async def genres(self, limit: int = 50) -> list[GenreData]:
        """Список жанров (/genre) — для выбора жанра в разделе «Топ»."""
        payload = await self._get_json("/genre", {"limit": limit})

        if not payload:
            return []

        items = payload.get("data") or []

        if not isinstance(items, list):
            return []

        genres: list[GenreData] = []

        for item in items:
            if not isinstance(item, dict):
                continue

            genre_id = item.get("id")
            name = item.get("name")

            if genre_id is None or not name:
                continue

            genres.append(GenreData(id=genre_id, name=name, picture_url=item.get("picture_medium")))

        return genres
