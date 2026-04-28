from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_main_menu() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏠 О хостеле")],
            [KeyboardButton(text="🛏 Номера и цены")],
            [KeyboardButton(text="📅 Забронировать")],
            [KeyboardButton(text="⭐ Отзывы"), KeyboardButton(text="📍 Как добраться")],
            [KeyboardButton(text="❌ Отменить бронь"), KeyboardButton(text="📞 Связь")],
        ],
        resize_keyboard=True
    )
    return keyboard