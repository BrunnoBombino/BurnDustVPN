import asyncio
from aiogram import Bot, Dispatcher

from bot.handlers import reg_router
from bot.handlers.user import user_router
from core.auth import BOT_TOKEN
from core.database import init_db
# Импортируй тут другие роутеры, когда они появятся

async def main():

    # ПРИНУДИТЕЛЬНО создаем таблицы
    init_db()
    print("Таблицы проверены/созданы.")

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Подключаем роутеры
    dp.include_router(user_router)
    dp.include_router(reg_router)

    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())