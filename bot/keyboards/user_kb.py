from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_start_keyboard() -> InlineKeyboardMarkup:
    """Кнопки первого экрана при старте"""
    buttons = []

    buttons.append([InlineKeyboardButton(text="📝 Создать новый аккаунт", callback_data="start_reg")])
    buttons.append([InlineKeyboardButton(text="🔗 Привязать аккаунт с сайта", callback_data="start_link")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_cabinet_keyboard() -> InlineKeyboardMarkup:
    """Интерфейс внутри личного кабинета"""
    buttons = [
        [InlineKeyboardButton(text="📊 Информация об аккаунте", callback_data="user_profile")],
        [InlineKeyboardButton(text="🚀 Получить VPN ссылки", callback_data="choose_link_type")],
        [InlineKeyboardButton(text="💳 Покупка / Продление подписки", callback_data="buy_menu")],
        [InlineKeyboardButton(text="❓ Помощь по подключению", callback_data="help_info")],
        [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)