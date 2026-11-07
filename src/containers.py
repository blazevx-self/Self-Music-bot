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
    DeezerClient,
    DownloaderService,
    TrackFileCache,
    TopService,
)
from src.services.common.new import NewReleasesService

session_context: ContextVar[AsyncSession] = ContextVar("session_context")

class Container(containers.DeclarativeContainer):
    config = providers.Configuration()
    bot = providers.Dependency(instance_of=Bot)

    db_session = providers.Factory(lambda: session_context.get(None))

    # repositories
    user_repo = providers.Factory(UserRepository, session=db_session)

    # services
    start_service = providers.Factory(StartService, user_repo=user_repo)

    deezer_client = providers.Singleton(DeezerClient)
    downloader_service = providers.Singleton(DownloaderService)
    search_service = providers.Singleton(SearchService, deezer=deezer_client)
    new_service = providers.Singleton(NewReleasesService, deezer=deezer_client)
    file_cache = providers.Singleton(TrackFileCache)
    top_service = providers.Singleton(TopService, deezer=deezer_client)