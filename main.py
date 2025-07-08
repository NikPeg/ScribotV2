import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from core import settings
from core.settings import LogLevel
from handlers import routers_list
from middlewares.logging_middleware import AdminLoggingMiddleware

async def main() -> None:
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Проверяем, нужно ли вообще включать логирование
    if settings.log_level == LogLevel.ALL:
        # .outer_middleware() сработает для любого входящего события
        dp.update.outer_middleware(AdminLoggingMiddleware())

    dp.include_routers(*routers_list)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped!")
