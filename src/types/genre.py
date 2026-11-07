from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GenreData:
    id: int
    name: str
    picture_url: str | None = None
