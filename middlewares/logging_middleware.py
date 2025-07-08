from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from core import settings

class AdminLoggingMiddleware(BaseMiddleware):
    """
    Middleware для отправки логов о действиях пользователей администратору.
    """
    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
    ) -> Any:
        # Получаем объект пользователя
        user = data.get('event_from_user')

        # Если пользователя нет или это сам админ, ничего не делаем
        if not user or user.id == settings.admin_id:
            return await handler(event, data)

        # Формируем сообщение для лога
        log_message = f"👤 Пользователь: {user.full_name} "
        if user.username:
            log_message += f"(@{user.username}) "
        log_message += f"[{user.id}]\n"

        if isinstance(event, Message):
            log_message += f"💬 Сообщение: {event.text or '[не текст]'}"
        elif isinstance(event, CallbackQuery):
            log_message += f"⚫️ Нажатие кнопки: `{event.data}`"

        # Отправляем лог админу в безопасном режиме
        try:
            await data['bot'].send_message(
                chat_id=settings.admin_id,
                text=log_message,
                parse_mode="Markdown" # Используем Markdown для `кода`
            )
        except Exception:
            # Если админ не запустил бота или заблокировал его,
            # мы просто игнорируем ошибку, чтобы бот не падал
            pass

        return await handler(event, data)
