import types

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import async_session

from bot.keyboards.user_kb import get_start_keyboard

user_router = Router()


@user_router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    tg_id = message.from_user.id

    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == tg_id))
        user = result.scalar_one_or_none()

        if user is None:
            text = (
                f"👋 Привет, {message.from_user.full_name}!\n\n"
                f"🛡️ Для использования VPN вам необходимо создать личный кабинет или "
                f"привязать аккаунт, если вы уже регистрировались на нашем сайте."
            )
            await message.answer(text=text, reply_markup=get_start_keyboard(needs_registration=True))
        else:
            text = (
                f"🔄 <b>Добро пожаловать в панель управления VPN!</b>\n\n"
                f"👤 Логин: <code>{user.username}</code>\n\n"
                f"Используйте кнопку ниже для открытия вашего Личного Кабинета ↓"
            )
            await message.answer(
                text=text,
                reply_markup=get_start_keyboard(needs_registration=False),
                parse_mode="HTML"
            )