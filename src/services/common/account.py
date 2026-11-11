import time

from src.database.mappers.account import orm_to_account
from src.database.repositories.account import AccountRepository

from src.types.data.account import AccountData
from src.types.data.track import TrackData
from src.types.data.user import UserData

from src.services.external.vk import VkClient, parse_profile_link

from src.utils.logger import system_logger

MAX_ACCOUNTS = 10 # лимит подключённых профилей на одного юзера
AUDIOS_TTL_SEC = 600 # кэш списка аудиозаписей профиля (в памяти процесса)

class AccountService:
    def __init__(self, account_repo: AccountRepository, vk: VkClient):
        self.account_repo = account_repo
        self.vk = vk
        self._audios_cache: dict[int, tuple[float, str, list[TrackData]]] = {}

    async def list_accounts(self, user: UserData) -> list[AccountData]:
        orms = await self.account_repo.list_by_user(user.id)
        return [orm_to_account(o) for o in orms]

    async def add_from_link(self, user: UserData, text: str) -> tuple[str, AccountData | None]:
        parsed = parse_profile_link(text)

        if parsed is None:
            return "invalid", None

        platform, screen_name = parsed

        accounts = await self.list_accounts(user)

        if len(accounts) >= MAX_ACCOUNTS:
            return "limit", None

        title = await self.vk.resolve_title(screen_name) or screen_name
        orm = await self.account_repo.upsert(user.id, platform, screen_name, title)

        system_logger.info(f"[ACCOUNTS] added | user_id={user.id} | {platform}:{screen_name} ({title})")
        return "ok", orm_to_account(orm)

    async def get_owned(self, account_id: int, user: UserData) -> AccountData | None:
        orm = await self.account_repo.get(account_id, user.id)
        return orm_to_account(orm) if orm else None

    async def delete_owned(self, account_id: int, user: UserData) -> bool:
        self._audios_cache.pop(account_id, None)
        deleted = await self.account_repo.delete(account_id, user.id)

        if deleted:
            system_logger.info(f"[ACCOUNTS] deleted | user_id={user.id} | account_id={account_id}")

        return deleted

    async def audios_status(self, account: AccountData) -> tuple[str, list[TrackData]]:
        now = time.monotonic()
        cached = self._audios_cache.get(account.id)

        if cached and now - cached[0] < AUDIOS_TTL_SEC:
            return cached[1], cached[2]

        if not self.vk.has_token:
            status, audios = "unavailable", []
        else:
            closed = await self.vk.is_closed(account.screen_name)

            if closed is None:
                status, audios = "unavailable", []
            elif closed:
                status, audios = "closed", []
            else:
                audios = await self.vk.get_audios(account.screen_name)
                # fallback: если error 28 или пусто — ищем по названию профиля
                if not audios:
                    title = await self.vk.resolve_title(account.screen_name)

                    if title:
                        audios = await self.vk.search_audios(title)

                status = "ok" if audios else "empty"

        self._audios_cache[account.id] = (now, status, audios)
        return status, audios

    def get_cached_audio(self, account_id: int, audio_id: int) -> TrackData | None:
        cached = self._audios_cache.get(account_id)

        if not cached:
            return None

        for track in cached[2]:
            if track.source_id == audio_id:
                return track

        return None