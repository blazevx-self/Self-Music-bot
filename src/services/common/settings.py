from src.core.exceptions.user import UserNotFoundError
from src.types.data.user import UserData

from src.database.repositories.user import UserRepository
from src.utils.logger import system_logger

class SettingsService:
    FLAGS = {
        "recognize": "recognize_enabled",
        "playlists": "playlists_enabled",
    }

    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def flags(self, user: UserData) -> dict[str, bool]:
        return {key: bool(getattr(user, column)) for key, column in self.FLAGS.items()}

    def is_enabled(self, user: UserData, key: str) -> bool:
        column = self.FLAGS.get(key)
        return bool(column and getattr(user, column, False))

    async def toggle(self, user: UserData, key: str) -> bool | None:
        column = self.FLAGS.get(key)

        if column is None:
            return None

        new_value = not getattr(user, column)

        try:
            await self.user_repo.change_data(user.telegram_id, **{column: new_value})
        except UserNotFoundError:
            system_logger.warning(f"[SETTINGS] toggle: user not found | telegram_id={user.telegram_id}")
            return not new_value

        system_logger.info(f"[SETTINGS] {key} -> {new_value} | telegram_id={user.telegram_id}")
        return new_value