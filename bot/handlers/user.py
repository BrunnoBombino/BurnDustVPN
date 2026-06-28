import types

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import async_session
from bot.keyboards.user_kb import get_start_keyboard
from bot.states.user_states import BindAccount
from bot.utils.db_utils import get_user_by_tg_id

user_router = Router()


@user_router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()

    # Теперь запрос выглядит так просто:
    user = await get_user_by_tg_id(message.from_user.id)

    if user is None:
        # Логика регистрации...
        await message.answer("Привет! Выберите действие:", reply_markup=get_start_keyboard(True))
    else:
        # Логика кабинета...
        await message.answer("С возвращением!", reply_markup=get_start_keyboard(False))

@user_router.callback_query(F.data == "start_link")
async def handle_start_link(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(BindAccount.waiting_for_token)
    await callback.message.edit_text(
        "🔗 **Привязка аккаунта**\n\n"
        "Введите токен, который вы получили в личном кабинете на сайте:",
        parse_mode="HTML"
    )


@user_router.message(BindAccount.waiting_for_token)
async def process_token_input(message: types.Message, state: FSMContext):
    token = message.text.strip()

    # Пытаемся привязать
    success = await bind_tg_to_user(message.from_user.id, token)

    if success:
        await message.answer("✅ Успешно! Аккаунт привязан.")
        await state.clear()
        # Можно сразу вызвать cmd_start, чтобы обновить клавиатуру на «Личный кабинет»
        await cmd_start(message, state)
    else:
        await message.answer("❌ Неверный токен. Попробуйте снова или нажмите /start для отмены.")