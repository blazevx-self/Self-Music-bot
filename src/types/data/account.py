from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class AccountData:
    id: int
    platform: str
    screen_name: str
    title: str