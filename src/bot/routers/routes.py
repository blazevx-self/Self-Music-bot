from src.bot.routers.common import (
    start, help, search,
    stub, new, top, collections,
    settings, account, recognition,
)

all_routers = (
    start.router,
    help.router,
    account.router,
    recognition.router,
    search.router,
    new.router,
    top.router,
    collections.router,
    settings.router,
    stub.router,
)

__all__ = ["all_routers"]