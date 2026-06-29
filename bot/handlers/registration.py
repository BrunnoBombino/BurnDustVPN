import re
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext

from bot.handlers.user import show_profile
from bot.states.user_states import Registration
from bot.utils.db_utils import check_user_exists
from core.database import async_session
from core.services import hash_password, create_user

reg_router = Router()


@reg_router.callback_query(F.data == "start_reg")
async def start_reg(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(Registration.waiting_for_login)
    await callback.message.edit_text("👤 Введите желаемый логин:")


@reg_router.message(Registration.waiting_for_login)
async def process_login(message: types.Message, state: FSMContext):
    login = message.text.strip()

    if await check_user_exists(login=login):
        await message.answer("❌ Этот логин уже занят. Попробуйте другой:")
        return

    await state.update_data(login=login)
    await state.set_state(Registration.waiting_for_password)
    await message.answer("🔑 Введите пароль:")


@reg_router.message(Registration.waiting_for_email)
async def process_email(message: types.Message, state: FSMContext):
    email = message.text.strip()

    # Валидация email...
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        await message.answer("❌ Некорректный формат email.")
        return

    # Получаем все собранные данные
    data = await state.get_data()

    # Сохраняем в БД (убедись, что в create_user модель принимает hash)
    async with async_session() as session:
        user = await create_user(
            db=session,
            email=email,
            password=data['password'],
            login=data['login'],
            tg_id=message.from_user.id
        )

    if user:
        await message.answer("✅ Регистрация завершена! Добро пожаловать в личный кабинет.")
        await show_profile(message, state)
    else:
        await message.answer("❌ Пользователь с таким email уже существует.")

    await state.clear()


@reg_router.message(Registration.waiting_for_password)
async def process_password(message: types.Message, state: FSMContext):
    password = message.text.strip()

    # Можно добавить проверку сложности
    if len(password) < 6:
        await message.answer("❌ Пароль слишком короткий (минимум 6 символов). Попробуйте еще раз:")
        return

    # Хешируем пароль сразу перед сохранением в state
    hashed_password = hash_password(password)
    await state.update_data(password=hashed_password)

    await state.set_state(Registration.waiting_for_email)
    await message.answer("📧 Теперь введите ваш email:")

