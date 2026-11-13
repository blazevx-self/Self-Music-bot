from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RecognizedTrack:
    artist: str
    title: str
    score: float | None = None
