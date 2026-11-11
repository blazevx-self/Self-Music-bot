from src.database.models.account import AccountOrm
from src.types.data.account import AccountData

def orm_to_account(orm: AccountOrm) -> AccountData:
    return AccountData(
        id=orm.id,
        platform=orm.platform,
        screen_name=orm.screen_name,
        title=orm.title
    )