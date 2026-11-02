from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from src.configs.yaml_loader import cfg

from src.bot.keyboards.common.start import back_keyboard

router = Router()

@router.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer(cfg["message"]["help"]["command"])

@router.callback_query(F.data == "menu:help")
async def help_menu(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        cfg["message"]["help"]["menu"],
        reply_markup=back_keyboard()
    )