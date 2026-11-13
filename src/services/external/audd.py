from __future__ import annotations

import aiohttp

from src.types.recognition import RecognizedTrack
from src.utils.logger import system_logger

AUDD_API_URL = "https://api.audd.io/"
MAX_AUDD_FILE_BYTES = 10 * 1024 * 1024

def _parse_response(payload: object) -> tuple[str, list[RecognizedTrack]]:
    if not isinstance(payload, dict) or payload.get("status") != "success":
        error = payload.get("error") if isinstance(payload, dict) else None
        code = error.get("error_code") if isinstance(error, dict) else "unknown"
        system_logger.warning(f"[AUDD] Recognition failed | code={code}")
        return "error", []

    result = payload.get("result")

    if result is None:
        return "empty", []

    if isinstance(result, dict) and isinstance(result.get("list"), list):
        candidates = result["list"]
    elif isinstance(result, dict):
        candidates = [result]
    elif isinstance(result, list):
        candidates = result
    else:
        return "empty", []

    matches: list[RecognizedTrack] = []

    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue

        artist = str(candidate.get("artist") or "").strip()
        title = str(candidate.get("title") or "").strip()

        if not artist or not title:
            continue

        try:
            score = float(candidate["score"]) if candidate.get("score") is not None else None
        except (TypeError, ValueError):
            score = None

        matches.append(RecognizedTrack(artist=artist, title=title, score=score))

    return ("ok", matches) if matches else ("empty", [])

class AudDClient:
    def __init__(self, token: str | None, timeout_sec: float = 25.0) -> None:
        self._token = token
        self._timeout_sec = aiohttp.ClientTimeout(total=timeout_sec)

    @property
    def configured(self) -> bool:
        return bool(self._token)

    async def recognize(
        self,
        audio: bytes,
        filename: str,
        *,
        humming: bool = False
    ) -> tuple[str, list[RecognizedTrack]]:
        if not self._token:
            return "error", []
        if not audio or len(audio) > MAX_AUDD_FILE_BYTES:
            return "error", []

        form = aiohttp.FormData()
        form.add_field("api_token", self._token)
        form.add_field(
            "file",
            audio,
            filename=filename or "audio.ogg",
            content_type="application/octet-stream"
        )

        if humming:
            form.add_field("method", "recognizeWithOffset")

        try:
            async with aiohttp.ClientSession(timeout=self._timeout_sec) as session:
                async with session.post(AUDD_API_URL, data=form) as response:
                    if response.status != 200:
                        system_logger.warning(f"[AUDD] HTTP {response.status}")
                        return "error", []

                    payload = await response.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as exc:
            system_logger.warning(f"[AUDD] Request failed | error={exc}")
            return "error", []

        return _parse_response(payload)