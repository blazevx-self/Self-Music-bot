from html import escape

from src.utils.logger import system_logger

async def notify_admin(
    bot,
    admin_id: int,
    user_info: str,
    event_name: str,
    process_time: float,
    error: str,
    traceback_text: str
) -> None:
    text = (
        "<b>Ошибка в Self Music</b>\n\n"
        f"👤 {escape(user_info)}\n"
        f"📦 {escape(event_name)}\n"
        f"⏱ {process_time}ms\n\n"
        f"<code>{escape(error[:500])}</code>\n"
        f"<pre>{escape(traceback_text[-1500:])}</pre>"
    )

    try:
        await bot.send_message(admin_id, text)
    except Exception as e:
        system_logger.error(f"[NOTIFIER] {e}")