"""
Сервис для проверки подписки пользователей на обязательные каналы.
"""
import logging
from aiogram import Bot
from core.settings import get_required_channels

logger = logging.getLogger(__name__)


async def check_user_subscription(
    bot: Bot, user_id: int, channels: list[str] = None
) -> dict[str, bool]:
    """
    Проверяет подписку пользователя на список каналов.

    Args:
        bot: Экземпляр бота
        user_id: ID пользователя
        channels: Список каналов для проверки (по умолчанию REQUIRED_CHANNELS)

    Returns:
        Словарь {channel: subscribed}, где subscribed = True если пользователь подписан
    """
    if channels is None:
        channels = get_required_channels()

    if not channels:
        # Если каналов нет, считаем что подписка не требуется
        return {}

    results = {}
    for channel in channels:
        try:
            # Получаем информацию о членстве пользователя в канале
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            # Проверяем статус пользователя
            # Статусы: creator, administrator, member - подписан
            # left, kicked - не подписан
            is_subscribed = member.status in ["creator", "administrator", "member"]
            results[channel] = is_subscribed
        except Exception as e:
            logger.error(f"Ошибка при проверке подписки на канал {channel}: {e}")
            # В случае ошибки считаем, что пользователь не подписан
            results[channel] = False

    return results


async def is_user_subscribed_to_all(bot: Bot, user_id: int, channels: list[str] = None) -> bool:
    """
    Проверяет, подписан ли пользователь на все обязательные каналы.

    Args:
        bot: Экземпляр бота
        user_id: ID пользователя
        channels: Список каналов для проверки (по умолчанию REQUIRED_CHANNELS)

    Returns:
        True если пользователь подписан на все каналы, False иначе
    """
    if channels is None:
        channels = get_required_channels()

    if not channels:
        # Если каналов нет, считаем что подписка не требуется
        return True

    subscription_status = await check_user_subscription(bot, user_id, channels)
    # Проверяем, что пользователь подписан на все каналы
    return all(subscription_status.values())

