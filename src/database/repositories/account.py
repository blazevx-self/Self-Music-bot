from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert

from src.database.models.account import AccountOrm
from src.database.repositories.base import Base

from src.utils.logger import database_logger

class AccountRepository(Base):
    async def list_by_user(self, user_id: int) -> list[AccountOrm]:
        stmt = (
            select(AccountOrm)
            .where(AccountOrm.user_id == user_id)
            .order_by(AccountOrm.created_at)
        )
        return list(await self.session.scalars(stmt))

    async def upsert(
        self,
        user_id: int,
        platform: str,
        screen_name: str,
        title: str,
    ) -> AccountOrm:
        stmt = (
            insert(AccountOrm)
            .values(
                user_id=user_id,
                platform=platform,
                screen_name=screen_name,
                title=title
            )
            .on_conflict_do_update(
                index_elements=["user_id", "platform", "screen_name"],
                set_={"title": title}
            )
            .returning(AccountOrm)
        )

        account = await self.session.scalar(stmt)

        if account is None:
            database_logger.error(
                f"[DB] Account not returned after UPSERT | user_id={user_id} | {platform}:{screen_name}"
            )
            raise ValueError("Account not returned after UPSERT")

        return account

    async def get(self, account_id: int, user_id: int) -> AccountOrm | None:
        stmt = (
            select(AccountOrm)
            .where(
                AccountOrm.id == account_id,
                AccountOrm.user_id == user_id
            )
        )
        return await self.session.scalar(stmt)

    async def delete(self, account_id: int, user_id: int) -> bool:
        stmt = delete(AccountOrm).where(
            AccountOrm.id == account_id,
            AccountOrm.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        return getattr(result, "rowcount", 0) > 0