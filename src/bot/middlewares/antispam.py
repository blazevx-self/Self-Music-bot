import time

from contextlib import suppress
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message, TelegramObject
from cachetools import TTLCache

from src.configs.yaml_loader import cfg
from src.utils.logger import system_logger


class CallbackSpamMiddleware(BaseMiddleware):
    """
    Middleware защиты от спама callback-кнопками (дебаунс).

    Блокирует повторные нажатия кнопок одним пользователем в течение
    короткого промежутка времени (time_limit), предотвращая параллельный
    запуск тяжёлых задач скачивания
    """

    def __init__(self, time_limit: float = 1.5) -> None:
        self.cache: TTLCache = TTLCache(maxsize=10_000, ttl=time_limit)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, CallbackQuery):
            return await handler(event, data)

        user_id = event.from_user.id

        if user_id in self.cache:
            system_logger.warning(
                f"[SPAM] Click is blocked | user_id={user_id} | data={event.data}"
            )

            with suppress(TelegramBadRequest):
                text = cfg.get("message", {}).get(
                    "antispam_button", "⏳ Подожди секунду перед следующим кликом"
                )
                await event.answer(text, show_alert=False)
            return None

        self.cache[user_id] = True
        return await handler(event, data)

class MessageFloodMiddleware(BaseMiddleware):
    """
    Middleware защиты от флуда текстовыми сообщениями.

    Реализует алгоритм скользящего окна времени: ограничивает количество
    входящих сообщений пользователя (не более max_messages за window_seconds).
    """

    def __init__(self, window_seconds: int = 5, max_messages: int = 3) -> None:
        self.cache: TTLCache = TTLCache(maxsize=10_000, ttl=window_seconds)
        self.window_seconds = window_seconds
        self.max_messages = max_messages

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message) or not event.from_user:
            return await handler(event, data)

        user_id = event.from_user.id
        now = time.monotonic()

        history = self.cache.get(user_id, [])
        history = [t for t in history if now - t < self.window_seconds]
        history.append(now)

        self.cache[user_id] = history

        if len(history) > self.max_messages:
            system_logger.warning(
                f"[FLOOD] Flood with messages | user_id={user_id} | requests={len(history)}"
            )
            if len(history) == self.max_messages + 1:
                await event.reply(
                    "<tg-emoji emoji-id=\"5386333827536809626\">🚫</tg-emoji> "
                    "Слишком много запросов. Подожди пару секунд перед следующим поиском."
                )
            return None

        return await handler(event, data)