from aiogram.fsm.state import State, StatesGroup

class BindAccount(StatesGroup):
    waiting_for_token = State()

class Registration(StatesGroup):
    waiting_for_login = State()
    waiting_for_password = State()
    waiting_for_email = State()

class States(StatesGroup):
    registration = Registration # Твои шаги регистрации
    main_menu = State()          # Состояние «Внутри ЛК»