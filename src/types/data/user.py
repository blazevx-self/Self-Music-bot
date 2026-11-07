from dataclasses import dataclass

@dataclass(slots=True)
class UserData:
    id: int
    telegram_id: int

    name: str
    username: str | None = None
    has_private_chat: bool = False

    language: str = "ru"
    is_subscribed: bool = False

    playlists_enabled: bool = False
    recognize_enabled: bool = False