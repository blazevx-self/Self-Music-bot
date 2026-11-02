from contextvars import ContextVar

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from dependency_injector import providers, containers

from src.database.repositories import (
    UserRepository,
)

from src.services import (
    StartService,
    SearchService,
)

session_context: ContextVar[AsyncSession] = ContextVar("session_context")

class Container(containers.DeclarativeContainer):
    config = providers.Configuration()
    bot = providers.Dependency(instance_of=Bot)

    db_session = providers.Factory(lambda: session_context.get(None))

    # repositories
    user_repo = providers.Factory(UserRepository, session=db_session)

    # services
    start_service = providers.Factory(StartService, user_repo=user_repo)
    search_service = providers.Singleton(SearchService)