import aiogram.exceptions

from aiogram import Bot
from aiogram.enums import ChatMemberStatus

from src.configs.settings import settings
from src.configs.yaml_loader import cfg

from src.core.enums.status import ResultStatus
from src.core.exceptions.user import UserNotFoundError

from src.types.data.user import UserData
from src.types.start_result import StartResult

from src.database.repositories.user import UserRepository
from src.utils.logger import start_logger

class StartService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    @staticmethod
    async def _is_channel_member(bot: Bot, user_id: int) -> bool:
        try:
            member = await bot.get_chat_member(
                chat_id=settings.CHANNEL_ID,
                user_id=user_id
            )
        except aiogram.exceptions.TelegramBadRequest as e:
            start_logger.warning(
                f"[START] Subscription check failed | user_id={user_id} | error={e}"
            )
            return False

        return member.status in (
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.CREATOR
        )

    async def _mark_subscribed(self, user_id: int) -> None:
        try:
            await self.user_repo.change_data(user_id, is_subscribed=True)
        except UserNotFoundError:
            start_logger.warning(
                f"[START] mark_subscribed: user not found | user_id={user_id}"
            )

    async def start(self, user: UserData, bot: Bot) -> StartResult:
        texts = cfg["message"]["start"]

        if user.is_subscribed or await self._is_channel_member(bot, user.telegram_id):
            if not user.is_subscribed:
                await self._mark_subscribed(user.telegram_id)

            return StartResult(status=ResultStatus.SUCCESS, text=texts["menu"])

        return StartResult(
            status=ResultStatus.NEED_SUBSCRIBE,
            text=texts["subscribe"],
        )

    async def confirm_subscription(self, user: UserData, bot: Bot) -> StartResult:
        texts = cfg["message"]["start"]

        if not await self._is_channel_member(bot, user.telegram_id):
            return StartResult(
                status=ResultStatus.NOT_SUBSCRIBED,
                text=texts["not_subscribed"],
            )

        await self._mark_subscribed(user.telegram_id)

        return StartResult(status=ResultStatus.SUCCESS, text=texts["menu"])