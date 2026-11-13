from dataclasses import dataclass

@dataclass(slots=True, frozen=True)
class RecognizedTrack:
    artist: str
    title: str
    score: float | None = None