from dataclasses import dataclass

@dataclass(slots=True, frozen=True)
class GenreData:
    id: int
    name: str
    picture_url: str | None = None