from src.bot.routers.common import start, help, accounts, search, new, top, collections, settings, stub

all_routers = (
    start.router,
    help.router,
    # «Аккаунты» — ДО search: его message-хендлер имеет фильтр состояния waiting_link,
    # поэтому при ЛЮБОМ другом состоянии текст проваливается дальше в поиск
    accounts.router,     # «Аккаунты»: menu:accounts, acc:*, accaud:*, vka:*, vkap:*
    search.router,
    new.router,          # «Новинки»: menu:new, npage:*, new:*
    top.router,          # «Топ»: menu:top, topg:*, tpage:*, top:*
    collections.router,  # «Подборки»: menu:mixes, mixg:*, mpage:*, mix:*
    settings.router,     # «Настройки»: menu:settings, set:*
    stub.router,         # catch-all для menu:* — строго последним
)

__all__ = ["all_routers"]
