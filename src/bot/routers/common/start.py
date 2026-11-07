from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery

from dependency_injector.wiring import inject, Provide

from src.containers import Container
from src.configs.yaml_loader import cfg

from src.core.enums.status import ResultStatus
from src.types.data.user import UserData

from src.services.common.start import StartService
from src.bot.keyboards.common.start import subscribe_keyboard, menu_keyboard

router = Router()

@router.message(CommandStart())
@inject
async def start_cmd(
    message: Message,
    user: UserData,
    bot: Bot,
    start_service: StartService = Provide[Container.start_service]
):
    result = await start_service.start(user=user, bot=bot)

    if result.status == ResultStatus.NEED_SUBSCRIBE:
        await message.answer(text=result.text, reply_markup=subscribe_keyboard())
        return

    await message.answer(text=result.text, reply_markup=menu_keyboard())

@router.callback_query(F.data == "sub:check")
@inject
async def check_subscription(
    callback: CallbackQuery,
    user: UserData,
    bot: Bot,
    start_service: StartService = Provide[Container.start_service]
):
    result = await start_service.confirm_subscription(user=user, bot=bot)

    if result.status == ResultStatus.NOT_SUBSCRIBED:
        await callback.answer(text=result.text, show_alert=True)
        return

    await callback.answer()
    await callback.message.edit_text(text=result.text, reply_markup=menu_keyboard())

@router.callback_query(F.data == "menu:back")
async def back_to_menu(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        cfg["message"]["start"]["menu"],
        reply_markup=menu_keyboard(),
    )