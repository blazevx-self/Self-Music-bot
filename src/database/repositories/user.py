from datetime import datetime

from sqlalchemy import select, update, case
from sqlalchemy.dialects.postgresql import insert

from src.core.exceptions.user import UserNotFoundError
from src.types.data.user import UserData

from src.database.models.user import UserOrm
from src.database.repositories.base import Base

from src.utils.logger import database_logger

class UserRepository(Base):
    async def upsert(
        self,
        telegram_id: int,
        name: str,
        username: str | None = None,
        has_private_chat: bool = False
    ) -> UserOrm:
        database_logger.debug(f"[DB] Upserting user: telegram_id={telegram_id} | name={name} | username={username}")

        stmt = (
            insert(UserOrm)
            .values(
                telegram_id=telegram_id,
                name=name,
                username=username,
                has_private_chat=has_private_chat
            )
            .on_conflict_do_update(
                index_elements=[UserOrm.telegram_id],
                set_={
                    "name": name,
                    "username": username,
                    "has_private_chat": case(
                        (UserOrm.has_private_chat.is_(True), True),
                        else_=has_private_chat
                    )
                }
            )
            .returning(UserOrm)
        )

        user = await self.session.scalar(stmt)

        if user is None:
            database_logger.error(f"[DB] User ({telegram_id}) not found after UPSERT")
            raise UserNotFoundError(f"User ({telegram_id}) not found after UPSERT")

        database_logger.debug(f"[DB] User upserted successfully: id={user.id}")

        return user

    async def get(self, search_parameter: int | str) -> UserOrm | None:
        database_logger.debug(f"[DB] Get user | search_parameter={search_parameter}")

        if isinstance(search_parameter, int):
            search_column = UserOrm.telegram_id
            search_type = "telegram_id"
        else:
            search_column = UserOrm.username
            search_type = "username"
            search_parameter = search_parameter.lstrip("@")

        stmt = select(UserOrm).where(search_column == search_parameter)

        user = await self.session.scalar(stmt)

        if user is None:
            database_logger.debug(f"[DB] User not found | {search_type}={search_parameter}")
            return None

        database_logger.debug(f"[DB] User found | id={user.id}")

        return user

    async def change_data(self, telegram_id: int, **kwargs) -> UserOrm:
        if not kwargs:
            raise ValueError("No fields to update")

        stmt = (
            update(UserOrm)
            .where(UserOrm.telegram_id == telegram_id)
            .values(**kwargs)
            .returning(UserOrm)
        )

        user = await self.session.scalar(stmt)

        if user is None:
            raise UserNotFoundError(f"User ({telegram_id}) not found")

        return user

    async def mark_subscribed(self, telegram_id: int) -> None:
        await self.change_data(telegram_id, is_subscribed=True)