import re

import aiohttp

from src.types.track import TrackData
from src.utils.logger import system_logger

VK_API_BASE = "https://api.vk.com/method"
VK_API_VERSION = "5.199"

_LINK_RE = re.compile(r"(?:https?://)?(?:www\.)?vk\.com/([A-Za-z0-9_.]+)", re.IGNORECASE)
_BARE_RE = re.compile(r"^@?([A-Za-z0-9_.]{3,32})$")


def parse_profile_link(text: str) -> tuple[str, str] | None:
    """
    «https://vk.com/id2586505556», «vk.com/dlyanxs», «@dlyanxs», «dlyanxs"
    -> ("vk", "dlyanxs"). None — не похоже на ссылку.
    Чтобы добавить другую площадку — расширяем эту функцию (platform уйдёт в БД как есть).
    """
    text = text.strip()

    m = _LINK_RE.search(text)
    if m:
        return "vk", m.group(1).lower()

    m = _BARE_RE.match(text)
    if m:
        return "vk", m.group(1).lower()

    return None


class VkClient:
    """
    Минимальный клиент VK API (только чтение публичных данных).

    Без VK_TOKEN в .env все методы возвращают None/[] — тогда раздел
    «Аудиозаписи» честно покажет алерт «недоступны». VK жёстко ограничивает
    audio.get для приложений, поэтому «недоступны/ошибка» — нормальный исход.
    """

    def __init__(self, token: str | None, timeout_sec: float = 10.0) -> None:
        self._token = token
        self._timeout = aiohttp.ClientTimeout(total=timeout_sec)

    @property
    def has_token(self) -> bool:
        return bool(self._token)

    async def _call(self, method: str, params: dict) -> dict | list | None:
        if not self._token:
            return None

        params = {**params, "access_token": self._token, "v": VK_API_VERSION}

        try:
            async with aiohttp.ClientSession(timeout=self._timeout) as session:
                async with session.get(f"{VK_API_BASE}/{method}", params=params) as resp:
                    data = await resp.json(content_type=None)
        except Exception as e:
            system_logger.warning(f"[VK] {method} request failed | error={e}")
            return None

        if not isinstance(data, dict) or "error" in data:
            system_logger.warning(f"[VK] {method} error | response={str(data)[:200]}")
            return None

        return data.get("response")

    async def _resolve(self, screen_name: str) -> tuple[str, int] | None:
        """
        Через utils.resolveScreenName узнаём, кто это: ("user"|"group", object_id).
        Работает для ЛЮБОГО screen_name («gooddaday», «club123», «id123», ник) —
        не надо угадывать по префиксу. None — не нашли/нет токена/ошибка.
        """
        resp = await self._call("utils.resolveScreenName", {"screen_name": screen_name})
        if isinstance(resp, dict) and resp.get("type") in ("user", "group") and resp.get("object_id"):
            try:
                return resp["type"], int(resp["object_id"])
            except (TypeError, ValueError):
                return None
        return None

    async def resolve_title(self, screen_name: str) -> str | None:
        """Отображаемое имя профиля/сообщества для кнопки. None — не удалось."""
        resolved = await self._resolve(screen_name)
        if resolved is None:
            return None

        kind, object_id = resolved
        if kind == "group":
            resp = await self._call("groups.getById", {"group_id": object_id})
            if isinstance(resp, dict):
                return resp.get("name")
            return None

        resp = await self._call("users.get", {"user_ids": object_id})
        if isinstance(resp, list) and resp:
            item = resp[0]
            name = f"{item.get('first_name', '')} {item.get('last_name', '')}".strip()
            return name or screen_name
        return None

    async def is_closed(self, screen_name: str) -> bool | None:
        """True — приватный/закрытый профиль. None — не удалось определить (нет токена/ошибка API)."""
        resolved = await self._resolve(screen_name)
        if resolved is None:
            return None

        kind, object_id = resolved
        if kind == "group":
            resp = await self._call("groups.getById", {"group_id": object_id})
            if isinstance(resp, dict):
                return bool(resp.get("is_closed")) or "deactivated" in resp
            return None

        resp = await self._call("users.get", {"user_ids": object_id, "fields": "can_access_closed,is_closed"})
        if isinstance(resp, list) and resp:
            item = resp[0]
            return bool(item.get("is_closed")) or not item.get("can_access_closed", True)
        return None

    async def get_audios(self, screen_name: str, limit: int = 50) -> list[TrackData]:
        """Аудиозаписи профиля/сообщества как TrackData (source_id = id аудио VK). Часто [] из-за ограничений VK."""
        resolved = await self._resolve(screen_name)
        if resolved is None:
            return []

        kind, object_id = resolved
        owner_id = -object_id if kind == "group" else object_id  # у сообщества владелец с минусом

        resp = await self._call("audio.get", {"owner_id": owner_id, "count": limit})
        items = resp.get("items", []) if isinstance(resp, dict) else []

        tracks: list[TrackData] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                tracks.append(TrackData(
                    source_id=int(item["id"]),
                    title=str(item.get("title", "")).strip(),
                    artist=str(item.get("artist", "")).strip(),
                    duration_sec=int(item.get("duration", 0)),
                    preview_url=str(item.get("url") or ""),
                ))
            except (KeyError, TypeError, ValueError):
                continue

        return [t for t in tracks if t.title and t.artist]

    async def search_audios(self, query: str, limit: int = 50) -> list[TrackData]:
        """
        Поиск аудио по запросу через VK API (разрешён для сервисного токена).
        Возвращает TrackData с source_id = id аудио VK (для ссылки в поиске).
        Если error 28/15/другое — возвращает [].
        """
        resp = await self._call("audio.search", {"q": query, "count": limit})
        if not isinstance(resp, dict) or "items" not in resp:
            return []

        items = resp["items"]
        tracks: list[TrackData] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                tracks.append(TrackData(
                    source_id=int(item["id"]),
                    title=str(item.get("title", "")).strip(),
                    artist=str(item.get("artist", "")).strip(),
                    duration_sec=int(item.get("duration", 0)),
                    preview_url=str(item.get("url") or ""),
                ))
            except (KeyError, TypeError, ValueError):
                continue

        return [t for t in tracks if t.title and t.artist]

