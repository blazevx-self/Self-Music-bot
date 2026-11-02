import asyncio
import aiohttp
import yt_dlp

from pathlib import Path
from typing import Any

from src.types.track import TrackData
from src.utils.logger import system_logger

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
    def __init__(self):
        self._last: dict[int, tuple[str, list[TrackData]]] = {}

    def remember(self, user_id: int, query: str, tracks: list[TrackData]) -> None:
        self._last[user_id] = (query, tracks)

    def page(self, user_id: int, page: int, per_page: int = 10):
        query, tracks = self._last.get(user_id, ("", []))
        start = page * per_page
        chunk = tracks[start : start + per_page]
        return query, chunk, len(tracks)

    def get_remembered(self, user_id: int, source_id: int) -> TrackData | None:
        _, tracks = self._last.get(user_id, ("", []))
        for track in tracks:
            if track.source_id == source_id:
                return track

        return None

    @staticmethod
    async def search(query: str) -> list[TrackData]:
        query = query.strip()

        if not query:
            return []

        timeout = aiohttp.ClientTimeout(total=10)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    DEEZER_SEARCH_URL,
                    params={"q": query}
                ) as response:
                    if response.status != 200:
                        system_logger.warning(
                            f"[SEARCH] Deezer HTTP {response.status} | q={query}"
                        )
                        return []

                    payload = await response.json()
        except aiohttp.ClientError as e:
            system_logger.warning(f"[SEARCH] Deezer request failed | q={query} | error={e}")
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

    @staticmethod
    async def download_track(artist: str, title: str, dest_dir: Path) -> Path | None:
        query = f"{artist} - {title}"
        out_tmpl = str(dest_dir / "%(id)s.%(ext)s")

        # noinspection SpellCheckingInspection
        ydl_opts: Any = {
            "format": "bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio",
            "outtmpl": out_tmpl,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "concurrent_fragment_downloads": 8,
            "buffersize": 1024 * 32,
            "extractor_args": {"youtube": {"player_client": ["mweb"]}},
        }

        def _download() -> Path | None:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                for source in (f"scsearch1:{query}", f"ytsearch1:{query} audio"):
                    try:
                        info: Any = ydl.extract_info(source, download=True)

                        if info and info.get("entries"):
                            return Path(ydl.prepare_filename(info["entries"][0]))
                    except Exception:
                        continue

            return None

        try:
            return await asyncio.to_thread(_download)
        except Exception as e:
            system_logger.error(f"[DOWNLOAD] Ошибка yt-dlp для «{query}»: {e}")
            return None