import time
import traceback

from typing import Any, Callable, Awaitable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from src.configs.settings import settings
from src.services.notifier import notify_admin
from src.utils.logger import bot_logger, callback_logger, error_logger

def _user_info(event, data) -> str:
    user = data.get("user")
    if user is not None:
        return f"name=\"{user.name}\" | user_id={user.telegram_id}"

    from_user = getattr(event, "from_user", None)
    if from_user is not None:
        return f"name=\"{from_user.first_name}\" | user_id={from_user.id}"

    return "Unknown"

class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        start = time.perf_counter()

        try:
            result = await handler(event, data)
            ping = round((time.perf_counter() - start) * 1000, 2)
            info = _user_info(event, data)

            if isinstance(event, Message) and event.text:
                bot_logger.info(
                    f"[COMMAND] {info} | chat={event.chat.type} | "
                    f"text=\"{event.text}\" | ping={ping}ms"
                )
            elif isinstance(event, CallbackQuery):
                callback_logger.info(
                    f"[CALLBACK] {info} | data=\"{event.data}\" | ping={ping}ms"
                )

            return result
        except Exception as e:
            ping = round((time.perf_counter() - start) * 1000, 2)
            info = _user_info(event, data)
            error_logger.exception(
                f"[ERROR] {info} | event={event.__class__.__name__} | ping={ping}ms"
            )

            bot = data.get("bot")

            if bot and settings.ADMIN_ID:
                await notify_admin(
                    bot=bot,
                    admin_id=settings.ADMIN_ID,
                    user_info=info,
                    event_name=event.__class__.__name__,
                    process_time=ping,
                    error=str(e),
                    traceback_text=traceback.format_exc(),
                )

            raise