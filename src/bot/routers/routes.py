from src.bot.routers.common import start, help, search, stub, new, top

all_routers = (
    start.router,
    help.router,
    search.router,
    new.router,
    top.router,
    stub.router,
)

__all__ = ["all_routers"]