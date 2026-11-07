from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CollectionData:
    id: int
    name: str
    query: str  # поисковый запрос Deezer — из него собирается подборка (топ по rank)
    min_year: int = 0  # фильтр по году выпуска альбома (0 = не фильтровать) — против «старья»
