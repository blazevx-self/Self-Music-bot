from src.bot.routers.common import start, help, search, new, top, collections, stub

all_routers = (
    start.router,
    help.router,
    search.router,
    new.router,          # «Новинки»: menu:new, npage:*, new:*
    top.router,          # «Топ»: menu:top, topg:*, tpage:*, top:*
    collections.router,  # «Подборки»: menu:mixes, mixg:*, mpage:*, mix:*
    stub.router,         # catch-all для menu:* — строго последним
)

__all__ = ["all_routers"]
