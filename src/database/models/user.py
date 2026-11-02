from datetime import datetime

from sqlalchemy import func, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import BigInteger

from src.database.models.base import Base

class UserOrm(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)

    name: Mapped[str] = mapped_column(nullable=False)
    username: Mapped[str | None] = mapped_column(nullable=True)
    has_private_chat: Mapped[bool] = mapped_column(default=False, nullable=False)

    language: Mapped[str] = mapped_column(String(8), default="ru", nullable=False)
    is_subscribed: Mapped[bool] = mapped_column(default=False, nullable=False)

    playlists_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    recognize_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())