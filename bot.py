import asyncio
import logging
from aiogram import Bot, Dispatcher

import config
from database import init_db
from handlers import start, grades, students, support, reports, developer
from utils.middleware import ActivationMiddleware

logging.basicConfig(level=logging.INFO)

async def main():
    if not config.BOT_TOKEN:
        logging.error("BOT_TOKEN is not set in environment or .env file.")
        return

    # Initialize SQLite tables
    init_db()

    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()

    # Register Middlewares
    dp.message.outer_middleware(ActivationMiddleware())

    # Register Routers — start.router MUST be last because it uses StateFilter("*")
    # which would intercept messages intended for specialized routers if registered first.
    dp.include_router(students.router)
    dp.include_router(grades.router)
    dp.include_router(reports.router)
    dp.include_router(developer.router)
    dp.include_router(support.router)
    dp.include_router(start.router)

    logging.info("Deleting webhook if it exists...")
    await bot.delete_webhook(drop_pending_updates=True)
    
    logging.info("Starting bot polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
