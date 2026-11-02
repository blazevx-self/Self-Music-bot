from typing import Any, Callable, Dict, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from aiogram.enums import ChatType

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.repositories.user import UserRepository
from src.database.mappers.user import orm_to_user

from src.utils.logger import database_logger

class SyncEntityUserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        tg_user = data.get("event_from_user")
        tg_chat = data.get("event_chat")

        if not tg_user or tg_user.is_bot:
            return None

        is_private = bool(tg_chat and tg_chat.type == ChatType.PRIVATE)
        session: AsyncSession = data["session"]

        try:
            user_repo = UserRepository(session)
            user_orm = await user_repo.upsert(
                telegram_id=tg_user.id,
                name=tg_user.first_name,
                username=tg_user.username,
                has_private_chat=is_private
            )

            data["user"] = orm_to_user(user_orm)
        except Exception:
            database_logger.exception(f"[DB] Entity sync failed | id={tg_user.id}")
            raise

        return await handler(event, data)