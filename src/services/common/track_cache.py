from cachetools import TTLCache

from src.types.data.track import TrackData

class TrackFileCache:
    def __init__(self, maxsize: int = 500, ttl: int = 24 * 3600) -> None:
        self._cache: TTLCache = TTLCache(maxsize=maxsize, ttl=ttl)

    @staticmethod
    def key_for(track: TrackData) -> str:
        if track.source_id:
            return f"deezer:{track.source_id}"

        return " ".join(f"{track.artist} - {track.title}".lower().split())

    def get(self, track: TrackData) -> str | None:
        return self._cache.get(self.key_for(track))

    def put(self, track: TrackData, file_id: str) -> None:
        self._cache[self.key_for(track)] = file_id

    def drop(self, track: TrackData) -> None:
        self._cache.pop(self.key_for(track), None)