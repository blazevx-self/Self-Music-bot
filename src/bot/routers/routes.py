from src.bot.routers.common import start, help, search, new, top, collections, settings, accounts, stub

all_routers = (
    start.router,
    help.router,
    search.router,
    new.router,          # «Новинки»: menu:new, npage:*, new:*
    top.router,          # «Топ»: menu:top, topg:*, tpage:*, top:*
    collections.router,  # «Подборки»: menu:mixes, mixg:*, mpage:*, mix:*
    settings.router,     # «Настройки»: menu:settings, set:*
    accounts.router,     # «Аккаунты»: menu:accounts, acc:*, accaud:*, vka:*, vkap:*
    stub.router,         # catch-all для menu:* — строго последним
)

__all__ = ["all_routers"]
