# utils/admin_logger.py
import contextlib
import html

from aiogram import Bot
from aiogram.types import User

from core import settings


async def send_admin_log(bot: Bot, user: User, log_details: str):
    """
    Формирует и отправляет сообщение с логом администратору.
    """
    # Проверяем, включено ли логирование и не является ли пользователь админом
    if settings.log_level.value == 'none' or user.id == settings.admin_id:
        return

    # Формируем сообщение
    safe_full_name = html.escape(user.full_name)
    log_message = f"👤 <b>Пользователь:</b> {safe_full_name}"
    if user.username:
        safe_username = html.escape(user.username)
        log_message += f" (@{safe_username})"
    log_message += f" [{user.id}]\n\n"
    log_message += f"<b>Действие:</b> {log_details}"

    # Отправляем лог
    with contextlib.suppress(Exception):
        await bot.send_message(
            chat_id=settings.admin_id,
            text=log_message,
            parse_mode="HTML"
        )
