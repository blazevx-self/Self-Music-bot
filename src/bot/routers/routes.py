from src.bot.routers.common import start, help, search

all_routers = (
    start.router,
    help.router,
    search.router,
)

__all__ = ["all_routers"]