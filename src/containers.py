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
    NewReleasesService,
    TopService,
    CollectionService,
    SettingsService,
    DownloaderService,
    TrackFileCache,
    DeezerClient,
)

session_context: ContextVar[AsyncSession] = ContextVar("session_context")

class Container(containers.DeclarativeContainer):
    config = providers.Configuration()
    bot = providers.Dependency(instance_of=Bot)

    db_session = providers.Factory(lambda: session_context.get(None))

    # repositories
    user_repo = providers.Factory(UserRepository, session=db_session)

    # external clients
    deezer_client = providers.Singleton(DeezerClient)

    # services
    start_service = providers.Factory(StartService, user_repo=user_repo)
    downloader_service = providers.Singleton(DownloaderService)
    search_service = providers.Singleton(SearchService, deezer=deezer_client)
    new_service = providers.Singleton(NewReleasesService, deezer=deezer_client)  # «Новинки»
    top_service = providers.Singleton(TopService, deezer=deezer_client)          # «Топ» по жанрам
    collection_service = providers.Singleton(CollectionService, deezer=deezer_client)  # «Подборки» по настроениям
    settings_service = providers.Factory(SettingsService, user_repo=user_repo)        # «Настройки»: toggle-флаги в users
    file_cache = providers.Singleton(TrackFileCache)                              # file_id скачанных треков
