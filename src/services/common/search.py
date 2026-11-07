from cachetools import TTLCache

from src.services.external.deezer import DeezerClient
from src.types.data.track import TrackData

DEEZER_SEARCH_URL = "https://api.deezer.com/search"

def _to_track(item: dict) -> TrackData | None:
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
        cover_url=cover
    )

class SearchService:
    def __init__(self, deezer: DeezerClient) -> None:
        self.deezer = deezer
        self._last: TTLCache = TTLCache(maxsize=1000, ttl=3600)

    def remember(self, user_id: int, query: str, tracks: list[TrackData]) -> None:
        self._last[user_id] = {
            "query": query,
            "tracks": tracks,
            "by_id": {t.source_id: t for t in tracks}
        }

    def page(self, user_id: int, page: int, per_page: int = 10):
        entry = self._last.get(user_id) or {"query": "", "tracks": []}
        tracks = entry["tracks"]
        start = page * per_page
        chunk = tracks[start: start + per_page]
        return entry["query"], chunk, len(tracks)

    def get_remembered(self, user_id: int, source_id: int) -> TrackData | None:
        entry = self._last.get(user_id)

        if entry is None:
            return None

        return entry["by_id"].get(source_id)

    async def search(self, query: str) -> list[TrackData]:
        return await self.deezer.search_tracks(query)