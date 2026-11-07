from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TrackData:
    source_id: int
    title: str
    artist: str
    duration_sec: int
    preview_url: str
    cover_url: str | None = None
    rank: int = 0  # popularity score Deezer (прослушивания) — для сортировки «топов»
    release_year: int = 0  # год выпуска альбома (release_date) — для фильтра «свежего»
