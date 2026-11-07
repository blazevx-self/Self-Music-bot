from src.bot.routers.common import start, help, search, new, top, stub

all_routers = (
    start.router,
    help.router,
    search.router,
    new.router,   # «Новинки»: menu:new, npage:*, new:*
    top.router,   # «Топ»: menu:top, topg:*, tpage:*, top:*
    stub.router,  # catch-all для menu:* — строго последним
)

__all__ = ["all_routers"]
