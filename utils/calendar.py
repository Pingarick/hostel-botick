from datetime import date, timedelta
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


# Русские названия месяцев
MONTHS = [
    "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
]

# Дни недели (пн-вс)
WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def get_calendar(year: int, month: int, selected_date: date | None = None) -> InlineKeyboardMarkup:
    """
    Генерирует инлайн-календарь на указанный месяц.
    selected_date — дата, которую гость уже выбрал (подсвечивается).
    """
    today = date.today()

    # Первый день месяца и количество дней
    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)

    # День недели первого числа (0 = пн, 6 = вс)
    start_weekday = first_day.weekday()

    # Строим клавиатуру
    keyboard = []

    # --- Заголовок: Месяц Год ---
    header = f"{MONTHS[month]} {year}"
    keyboard.append([
        InlineKeyboardButton(
            text=f"« {MONTHS[month]} »",
            callback_data="calendar:ignore"  # заголовок не кликабельный
        )
    ])

    # --- Дни недели ---
    keyboard.append([
        InlineKeyboardButton(text=day, callback_data="calendar:ignore")
        for day in WEEKDAYS
    ])

    # --- Дни месяца ---
    current_day = 1
    # Первая строка — может начинаться с пустых кнопок
    for week in range(6):  # максимум 6 строк
        row = []
        for weekday in range(7):
            if week == 0 and weekday < start_weekday:
                # Пустые клетки до первого числа
                row.append(InlineKeyboardButton(text=" ", callback_data="calendar:ignore"))
            elif current_day > last_day.day:
                # Дни закончились — добиваем строку пустыми кнопками
                row.append(InlineKeyboardButton(text=" ", callback_data="calendar:ignore"))
            else:
                day_date = date(year, month, current_day)

                # Определяем текст кнопки
                if day_date < today:
                    # Прошедшие даты — заблокированы
                    day_text = "✕"
                elif selected_date and day_date == selected_date:
                    # Выбранная дата — подсвечиваем
                    day_text = f"[{current_day}]"
                else:
                    day_text = str(current_day)

                # Callback для прошедших дат — игнорируем
                if day_date < today:
                    callback_data = "calendar:ignore"
                else:
                    callback_data = f"calendar:day:{day_date.isoformat()}"

                row.append(InlineKeyboardButton(
                    text=day_text,
                    callback_data=callback_data
                ))
                current_day += 1

        keyboard.append(row)

        # Если дни закончились — прекращаем
        if current_day > last_day.day:
            break

    # --- Навигация: назад / сегодня / вперёд ---
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    navigation = [
        InlineKeyboardButton(text="◀", callback_data=f"calendar:month:{prev_year}:{prev_month}"),
        InlineKeyboardButton(text="Сегодня", callback_data=f"calendar:today"),
        InlineKeyboardButton(text="▶", callback_data=f"calendar:month:{next_year}:{next_month}"),
    ]

    keyboard.append(navigation)
    # Кнопка отмены
    keyboard.append([
        InlineKeyboardButton(text="❌ Отмена", callback_data="booking:cancel")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)