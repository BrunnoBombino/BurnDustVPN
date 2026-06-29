from aiogram import Router,types, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from bot.keyboards.user_kb import get_start_keyboard, get_cabinet_keyboard
from bot.states.user_states import BindAccount, States
from bot.utils.db_utils import get_user_by_tg_id, bind_tg_to_user
from core.database import async_session, User

user_router = Router()


@user_router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()

    user = await get_user_by_tg_id(message.from_user.id)

    if user:
        # Прямой вход для зарегистрированных
        await show_profile(message, state)
    else:
        # Для новых — классическое приветствие
        await message.answer(
            "Привет! Я помогу управлять вашим VPN. Выберите действие:",
            reply_markup=get_start_keyboard()
        )


# 1. Запуск процесса привязки (кнопка в меню)
@user_router.callback_query(F.data == "start_link")
async def handle_start_link(callback: types.CallbackQuery, state: FSMContext):
    # Переводим бота в состояние ожидания токена
    await state.set_state(BindAccount.waiting_for_token)
    await callback.message.edit_text("🔗 Введите ваш токен привязки:")



# 2. Обработка ввода (только если бот в состоянии waiting_for_token)
@user_router.message(BindAccount.waiting_for_token)
async def process_token(message: types.Message, state: FSMContext):
    token = message.text.strip()

    # Пытаемся привязать через функцию из db_utils
    if await bind_tg_to_user(message.from_user.id, token):
        await message.answer("✅ Аккаунт успешно привязан!")
        await state.clear()  # Выходим из состояния ожидания
    else:
        await message.answer("❌ Токен не найден. Попробуйте еще раз или /start для отмены.")


@user_router.message(StateFilter(None), F.text == "Личный кабинет")
@user_router.callback_query(F.data == "show_profile")
async def show_profile(message: types.Message | types.CallbackQuery, state: FSMContext):
    tg_id = message.from_user.id

    async with async_session() as session:
        # Ищем юзера по его Telegram ID
        result = await session.execute(select(User).where(User.telegram_id == tg_id))
        user = result.scalar_one_or_none()

    if user:
        await state.set_state(States.main_menu)
        text = (f"👤 **Ваш профиль**\n\n"
                f"Логин: {user.username}\n"
                f"Email: {user.email}")

        if isinstance(message, types.CallbackQuery):
            await message.message.edit_text(text)
        else:
            await message.answer(text, reply_markup=get_cabinet_keyboard())
    else:
        await message.answer("❌ Вы еще не зарегистрированы.")

