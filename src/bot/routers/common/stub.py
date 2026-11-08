from aiogram import F, Router
from aiogram.types import CallbackQuery

router = Router()


@router.callback_query(F.data.startswith("menu:"))
async def menu_stub(callback: CallbackQuery):
    """
    Catch-all для пунктов меню без реализации (playlists и др.).
    Регистрируется ПОСЛЕДНИМ роутером, чтобы не перехватывать menu:back / menu:help / menu:new / menu:top.
    """
    await callback.answer("🚧 Этот раздел пока в разработке", show_alert=False)
