from dataclasses import dataclass

@dataclass(slots=True, frozen=True)
class CollectionData:
    id: int
    name: str
    query: str