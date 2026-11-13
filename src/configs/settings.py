from pydantic import SecretStr, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = Field(default=...)
    BOT_TOKEN: SecretStr = Field(default=...)
    ADMIN_ID: int = Field(default=...)

    CHANNEL_ID: int = Field(default=...)
    CHANNEL_URL: str = Field(default=...)

    # Опционально: прокси для yt-dlp (например socks5h://127.0.0.1:1080),
    # если YouTube/SoundCloud недоступны напрямую с сервера (блокировка/DNS)
    YTDLP_PROXY: str | None = Field(default=None)

    # Опционально: токен VK API для раздела «Аккаунты».
    VK_TOKEN: str | None = Field(default=None)

    # Опционально: API-токен AudD для распознавания музыки и напева.
    AUDD_API_TOKEN: SecretStr | None = Field(default=None)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()