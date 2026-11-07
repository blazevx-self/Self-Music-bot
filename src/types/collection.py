from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CollectionData:
    id: int
    name: str
    query: str  # поисковый запрос Deezer — из него собирается подборка (топ по rank)
