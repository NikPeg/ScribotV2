import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from core import settings
from handlers import routers_list

async def main() -> None:
    # Инициализация бота и диспетчера
    bot = Bot(token=settings.bot_token, parse_mode=ParseMode.HTML)
    dp = Dispatcher()

    # Включаем все роутеры из списка
    dp.include_routers(*routers_list)

    # Удаляем вебхук, если он был установлен ранее, чтобы не мешать поллингу
    await bot.delete_webhook(drop_pending_updates=True)

    # Запускаем поллинг
    await dp.start_polling(bot)

if __name__ == "__main__":
    # Настраиваем логирование
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    # Запускаем асинхронную функцию main
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped!")
