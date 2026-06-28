from aiogram.fsm.state import State, StatesGroup

class BindAccount(StatesGroup):
    waiting_for_token = State()