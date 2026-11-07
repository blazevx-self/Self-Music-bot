from src.core.exceptions.user import UserNotFoundError
from src.database.repositories.user import UserRepository
from src.types.user_entity import UserData
from src.utils.logger import system_logger


class SettingsService:
    """
    «Настройки»: переключатели функций бота (boolean-поля таблицы users).

    Ключ настройки -> колонка БД только из белого списка FLAGS — через callback
    нельзя дёрнуть произвольное поле пользователя. Commit транзакции — в
    DatabaseMiddleware после успешного хендлера.
    """

    FLAGS = {
        "recognize": "recognize_enabled",
        "playlists": "playlists_enabled",
    }

    def __init__(self, user_repo: UserRepository) -> None:
        self.user_repo = user_repo

    def flags(self, user: UserData) -> dict[str, bool]:
        """Текущие значения всех настроек пользователя."""
        return {key: bool(getattr(user, column)) for key, column in self.FLAGS.items()}

    def is_enabled(self, user: UserData, key: str) -> bool:
        """Для будущих роутеров распознавания/плейлистов: включена ли фича у юзера."""
        column = self.FLAGS.get(key)
        return bool(column and getattr(user, column, False))

    async def toggle(self, user: UserData, key: str) -> bool | None:
        """Переключить настройку и сохранить в БД; вернуть новое значение. None — чужой ключ."""
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
