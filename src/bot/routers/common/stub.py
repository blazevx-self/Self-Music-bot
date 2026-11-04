from aiogram import Router, F
from aiogram.types import CallbackQuery

router = Router()

@router.callback_query(F.data.startswith("menu:"))
async def menu_stub(callback: CallbackQuery):
    await callback.answer("🚧 Этот раздел пока в разработке", show_alert=False)