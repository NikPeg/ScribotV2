"""
Обработчики для проверки подписки на обязательные каналы.
"""
import logging
from aiogram import Router, Bot
from aiogram.types import CallbackQuery
from services.subscription_service import is_user_subscribed_to_all
from keyboards.inline_keyboards import get_subscription_keyboard
from utils.admin_logger import send_admin_log

logger = logging.getLogger(__name__)

subscription_router = Router()

# Сообщения для пользователя
SUBSCRIPTION_REQUIRED_MESSAGE = (
    "🔔 <b>Для использования бота необходимо подписаться на наши каналы!</b>\n\n"
    "Пожалуйста, подпишитесь на все указанные каналы и нажмите кнопку «✅ Я подписался»."
)

SUBSCRIPTION_VERIFIED_MESSAGE = (
    "✅ <b>Отлично! Подписка подтверждена.</b>\n\n"
    "Теперь вы можете использовать бота для генерации работ."
)

SUBSCRIPTION_NOT_VERIFIED_MESSAGE = (
    "❌ <b>Вы еще не подписались на все каналы.</b>\n\n"
    "Пожалуйста, убедитесь, что вы подписались на все указанные каналы и попробуйте снова."
)


@subscription_router.callback_query(lambda c: c.data == "check_subscription")
async def process_subscription_check(callback_query: CallbackQuery, bot: Bot):
    """
    Обработчик нажатия на кнопку "Я подписался".
    Проверяет подписку пользователя на все обязательные каналы.
    """
    user_id = callback_query.from_user.id
    
    try:
        # Проверяем подписку
        is_subscribed = await is_user_subscribed_to_all(bot, user_id)
        
        if is_subscribed:
            # Пользователь подписан на все каналы
            logger.info(f"USER{user_id}: подписка подтверждена")
            await callback_query.answer(
                text="✅ Подписка подтверждена!",
                show_alert=False
            )
            # Удаляем сообщение с просьбой подписаться
            await callback_query.message.delete()
            # Отправляем подтверждение
            await bot.send_message(
                chat_id=user_id,
                text=SUBSCRIPTION_VERIFIED_MESSAGE
            )
            await send_admin_log(bot, callback_query.from_user, "Подтвердил подписку на каналы")
        else:
            # Пользователь не подписан на все каналы
            logger.info(f"USER{user_id}: попытка подтвердить подписку, но не подписан на все каналы")
            await callback_query.answer(
                text="❌ Вы еще не подписались на все каналы",
                show_alert=True
            )
    except Exception as e:
        logger.error(f"Ошибка при проверке подписки для USER{user_id}: {e}")
        await callback_query.answer(
            text="❌ Произошла ошибка при проверке подписки. Попробуйте позже.",
            show_alert=True
        )

