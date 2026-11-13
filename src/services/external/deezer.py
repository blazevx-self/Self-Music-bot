import aiohttp

from src.types.data.track import TrackData
from src.types.data.genre import GenreData

from src.utils.logger import system_logger

DEEZER_BASE_URL = "https://api.deezer.com"

def _to_track(item: dict) -> TrackData | None:
    preview = item.get("preview") or ""

    if not preview:
        return None

    artist = (item.get("artist") or {}).get("name") or ""
    title = item.get("title") or ""

    if not artist or not title:
        return None

    album = item.get("album") or {}
    cover = album.get("cover_medium")

    release_date = album.get("release_date") or ""

    try:
        release_year = int(release_date[:4]) if release_date else 0
    except ValueError:
        release_year = 0

    return TrackData(
        source_id=item["id"],
        title=title,
        artist=artist,
        duration_sec=item.get("duration") or 0,
        preview_url=preview,
        cover_url=cover,
        rank=item.get("rank") or 0,
        release_year=release_year
    )

class DeezerClient:
    """Единая точка доступа к публичному API Deezer (ключ не требуется)."""

    def __init__(self, timeout_sec: float = 10.0) -> None:
        self._timeout = aiohttp.ClientTimeout(total=timeout_sec)

    async def _get_json(self, path: str, params: dict) -> dict | None:
        try:
            async with aiohttp.ClientSession(timeout=self._timeout) as session:
                async with session.get(DEEZER_BASE_URL + path, params=params) as resp:
                    if resp.status != 200:
                        system_logger.warning(
                            f"[DEEZER] HTTP {resp.status} | path={path} | params={params}"
                        )
                        return None
                    return await resp.json()
        except TimeoutError:
            system_logger.warning(f"[DEEZER] Request timed out | path={path}")
            return None
        except (aiohttp.ClientError, ValueError) as e:
            system_logger.warning(
                f"[DEEZER] Request failed | path={path} | error={e}"
            )
            return None

    @staticmethod
    def _parse_tracks(payload: dict | None) -> list[TrackData]:
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
        query = query.strip()

        if not query:
            return []

        payload = await self._get_json("/search", {"q": query, "limit": limit})
        return self._parse_tracks(payload)

    async def world_chart_tracks(self, limit: int = 70) -> list[TrackData]:
        payload = await self._get_json("/chart/0/tracks", {"limit": limit})
        return self._parse_tracks(payload)
    
    async def genre_chart_tracks(self, genre_id: int, limit: int = 70) -> list[TrackData]:
        payload = await self._get_json(f"/chart/{genre_id}/tracks", {"limit": limit})
        return self._parse_tracks(payload)

    async def top_by_query(self, query: str, limit: int = 75, min_year: int = 0) -> list[TrackData]:
        payload = await self._get_json("/search", {"q": query, "limit": 100})
        tracks = self._parse_tracks(payload)
        tracks.sort(key=lambda t: t.rank, reverse=True)

        if min_year:
            fresh = [t for t in tracks if t.release_year >= min_year]

            if fresh:
                tracks = fresh

        return tracks[:limit]

    async def genres(self, limit: int = 50) -> list[GenreData]:
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

            genres.append(GenreData(
                id=genre_id,
                name=name,
                picture_url=item.get("picture_medium")
            ))
           
        return genres