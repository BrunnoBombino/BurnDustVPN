from aiogram import Bot, Dispatcher
from bot.handlers import routers
from core.auth import BOT_TOKEN


async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Подключаем все роутеры одной строкой
    dp.include_routers(*routers)

    await dp.start_polling(bot)