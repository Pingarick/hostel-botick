import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers.user import user_router
from handlers.admin import admin_router
from database.db import init_db
from utils.scheduler import reminder_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

dp.include_router(user_router)
dp.include_router(admin_router)


async def main():
    init_db()
    logging.info("База данных готова")

    asyncio.create_task(reminder_loop(bot, interval_hours=1))
    logging.info("Фоновая задача напоминаний запущена (каждый час)")

    logging.info("Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())