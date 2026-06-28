from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_start_keyboard(needs_registration: bool) -> InlineKeyboardMarkup:
    """Кнопки первого экрана при старте"""
    buttons = []
    if needs_registration:
        buttons.append([InlineKeyboardButton(text="📝 Создать новый аккаунт", callback_data="start_reg")])
        buttons.append([InlineKeyboardButton(text="🔗 Привязать аккаунт с сайта", callback_data="start_link")])
    else:
        buttons.append([InlineKeyboardButton(text="👤 Личный кабинет", callback_data="open_cabinet")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)