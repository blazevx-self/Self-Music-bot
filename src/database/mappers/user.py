from src.database.models.user import UserOrm
from src.types.data.user import UserData

def orm_to_user(user: UserOrm) -> UserData:
    return UserData(
        id=user.id,
        telegram_id=user.telegram_id,

        name=user.name,
        username=user.username,
        has_private_chat=user.has_private_chat,

        language=user.language,
        is_subscribed=user.is_subscribed,

        playlists_enabled=user.playlists_enabled,
        recognize_enabled=user.recognize_enabled
    )