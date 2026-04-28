from datetime import datetime, date

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from keyboards import get_main_menu

user_router = Router()


# ============================================================
#  FSM: СОСТОЯНИЯ
# ============================================================

class BookingState(StatesGroup):
    choosing_room = State()
    choosing_check_in = State()
    choosing_check_out = State()
    entering_beds = State()
    entering_name = State()
    entering_phone = State()
    confirming = State()


class ContactState(StatesGroup):
    writing_message = State()


class ReviewState(StatesGroup):
    waiting_for_rating = State()
    waiting_for_text = State()


# ============================================================
#  /start
# ============================================================

@user_router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        f"👋 Добро пожаловать!\n\n"
        f"Выберите действие в меню ниже:",
        reply_markup=get_main_menu()
    )


# ============================================================
#  🏠 О ХОСТЕЛЕ
# ============================================================

@user_router.message(F.text == "🏠 О хостеле")
async def about_hostel(message: Message):
    from config import HOSTEL_NAME

    text = (
        f"🏠 {HOSTEL_NAME}\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"Уютный хостел в самом центре Казани.\n"
        f"Пешком до Кремля — 5 минут, до метро — 3 минуты.\n\n"
        f"🕐 Заезд: с 14:00\n"
        f"🕐 Выезд: до 12:00\n\n"
        f"✨ Удобства:\n"
        f"• Бесплатный Wi-Fi\n"
        f"• Кухня (чай, кофе — бесплатно)\n"
        f"• Прачечная\n"
        f"• Круглосуточная стойка\n"
        f"• Камеры хранения багажа\n\n"
        f"Ждём вас в гости! 🏠"
    )
    await message.answer(text)


# ============================================================
#  🛏 НОМЕРА И ЦЕНЫ
# ============================================================

@user_router.message(F.text == "🛏 Номера и цены")
async def rooms_prices(message: Message):
    from database.db import get_connection

    conn = get_connection()
    rooms = conn.execute(
        "SELECT name, total_beds, price_per_night FROM rooms"
    ).fetchall()
    conn.close()

    if not rooms:
        await message.answer("Информация о номерах скоро появится!")
        return

    text = "🛏 Номера и цены\n"
    text += "━━━━━━━━━━━━━━━━\n\n"
    for room in rooms:
        text += f"• {room['name']}\n"
        text += f"   {room['total_beds']} мест · {room['price_per_night']} ₽/ночь\n\n"

    text += "Цена указана за одно место."

    await message.answer(text)


# ============================================================
#  📍 КАК ДОБРАТЬСЯ
# ============================================================

@user_router.message(F.text == "📍 Как добраться")
async def how_to_get(message: Message):
    text = (
        f"📍 Как нас найти\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"🏠 Адрес: ул. Баумана, 5, Казань\n\n"
        f"🚇 Ближайшее метро: Кремлёвская (3 мин)\n\n"
        f"🚌 Остановка: ул. Баумана\n"
        f"Автобусы: 2, 10, 31, 53\n\n"
        f"🚂 От ж/д вокзала: 10 мин на автобусе №2\n"
        f"✈️ От аэропорта: электричка до вокзала + 10 мин\n\n"
        f"🗺 Открыть на Яндекс.Картах:\n"
        f"https://yandex.ru/maps/43/kazan/"
    )
    await message.answer(text, disable_web_page_preview=True)


# ============================================================
#  📞 СВЯЗЬ
# ============================================================

@user_router.message(StateFilter(None), F.text == "📞 Связь")
async def contact_start(message: Message, state: FSMContext):
    cancel_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
    )

    await message.answer(
        f"📞 Связь с администратором\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"Напишите ваш вопрос, и мы ответим в ближайшее время.\n\n"
        f"Для отмены нажмите кнопку ниже.",
        reply_markup=cancel_keyboard
    )
    await state.set_state(ContactState.writing_message)


@user_router.message(ContactState.writing_message, F.text == "❌ Отмена")
async def contact_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Обращение отменено.", reply_markup=get_main_menu())


@user_router.message(ContactState.writing_message)
async def contact_send(message: Message, state: FSMContext):
    from config import ADMIN_IDS

    for admin_id in ADMIN_IDS:
        try:
            await message.bot.send_message(
                admin_id,
                f"📞 Новое обращение\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"👤 {message.from_user.full_name}\n"
                f"🆔 ID: {message.from_user.id}\n"
                f"📩 @{message.from_user.username or 'нет'}\n\n"
                f"💬 Сообщение:\n{message.text}"
            )
        except Exception:
            pass

    await state.clear()
    await message.answer(
        "✅ Сообщение отправлено!\n"
        "Администратор свяжется с вами в ближайшее время.",
        reply_markup=get_main_menu()
    )


# ============================================================
#  📅 БРОНИРОВАНИЕ — Шаг 1: выбор номера
# ============================================================

@user_router.message(StateFilter(None), F.text == "📅 Забронировать")
async def start_booking(message: Message, state: FSMContext):
    from database.db import get_connection

    conn = get_connection()
    rooms = conn.execute("SELECT type, name FROM rooms").fetchall()
    conn.close()

    buttons = []
    for room in rooms:
        buttons.append([KeyboardButton(text=room["name"])])
    buttons.append([KeyboardButton(text="❌ Отмена")])

    room_keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

    await message.answer("Выберите тип номера:", reply_markup=room_keyboard)
    await state.set_state(BookingState.choosing_room)


# ============================================================
#  БРОНИРОВАНИЕ — Шаг 2: выбор номера → календарь заезда
# ============================================================

@user_router.message(BookingState.choosing_room, F.text != "❌ Отмена")
async def room_chosen(message: Message, state: FSMContext):
    from database.db import get_connection
    from utils.calendar import get_calendar
    from datetime import date

    room_name = message.text

    conn = get_connection()
    room = conn.execute(
        "SELECT id, type, name FROM rooms WHERE name = ?",
        (room_name,)
    ).fetchone()
    conn.close()

    if room is None:
        await message.answer("Пожалуйста, выберите номер из списка кнопок.")
        return

    await state.update_data(
        room_id=room["id"],
        room_type=room["type"],
        room_name=room["name"]
    )

    today = date.today()

    await message.answer(
        f"Вы выбрали: {room['name']}\n\n"
        f"📅 Выберите дату заезда:\n"
        f"Доступные дни выделены числами.\n"
        f"Прошедшие даты заблокированы (✕).",
        reply_markup=get_calendar(today.year, today.month)
    )
    await state.set_state(BookingState.choosing_check_in)


# ============================================================
#  БРОНИРОВАНИЕ — Отмена на любом шаге (текстовая кнопка)
# ============================================================

@user_router.message(StateFilter(BookingState), F.text == "❌ Отмена")
async def booking_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Бронирование отменено.", reply_markup=get_main_menu())


# ============================================================
#  БРОНИРОВАНИЕ — Обработчик календаря
# ============================================================

@user_router.callback_query(F.data.startswith("calendar:"))
async def calendar_handler(callback: CallbackQuery, state: FSMContext):
    from utils.calendar import get_calendar
    from datetime import date

    parts = callback.data.split(":")

    if parts[1] == "ignore":
        await callback.answer()
        return

    current_state = await state.get_state()
    data = await state.get_data()
    today = date.today()

    # Навигация по месяцам
    if parts[1] == "month":
        year = int(parts[2])
        month = int(parts[3])

        selected = None
        if current_state == BookingState.choosing_check_in and "check_in" in data:
            selected = date.fromisoformat(data["check_in"])
        elif current_state == BookingState.choosing_check_out and "check_out" in data:
            selected = date.fromisoformat(data["check_out"])

        await callback.message.edit_reply_markup(
            reply_markup=get_calendar(year, month, selected)
        )
        await callback.answer()

    # Кнопка "Сегодня"
    elif parts[1] == "today":
        selected = None
        if current_state == BookingState.choosing_check_in and "check_in" in data:
            selected = date.fromisoformat(data["check_in"])
        elif current_state == BookingState.choosing_check_out and "check_out" in data:
            selected = date.fromisoformat(data["check_out"])

        await callback.message.edit_reply_markup(
            reply_markup=get_calendar(today.year, today.month, selected)
        )
        await callback.answer()

    # Выбор дня
    elif parts[1] == "day":
        chosen_date = date.fromisoformat(parts[2])

        if current_state == BookingState.choosing_check_in:
            await state.update_data(check_in=chosen_date.isoformat())
            await callback.message.edit_text(
                f"📅 Дата заезда: {chosen_date.strftime('%d.%m.%Y')}\n\n"
                f"Теперь выберите дату выезда:",
                reply_markup=get_calendar(chosen_date.year, chosen_date.month)
            )
            await state.set_state(BookingState.choosing_check_out)
            await callback.answer()

        elif current_state == BookingState.choosing_check_out:
            check_in = date.fromisoformat(data["check_in"])

            if chosen_date <= check_in:
                await callback.answer(
                    "❌ Дата выезда должна быть позже даты заезда",
                    show_alert=True
                )
                return

            await state.update_data(check_out=chosen_date.isoformat())
            await callback.answer()
            await check_availability_and_proceed(callback.message, state)


# ============================================================
#  БРОНИРОВАНИЕ — Отмена из календаря
# ============================================================

@user_router.callback_query(F.data == "booking:cancel")
async def calendar_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer(
        "Бронирование отменено.",
        reply_markup=get_main_menu()
    )
    await callback.answer("Отменено")


# ============================================================
#  БРОНИРОВАНИЕ — Проверка доступности после выбора дат
# ============================================================

async def check_availability_and_proceed(message: Message, state: FSMContext):
    from database.db import get_connection
    from datetime import date
    from utils.calendar import get_calendar

    data = await state.get_data()
    check_in = date.fromisoformat(data["check_in"])
    check_out = date.fromisoformat(data["check_out"])

    conn = get_connection()
    room_id = data["room_id"]
    room_type = data["room_type"]

    existing = conn.execute(
        """
        SELECT COUNT(*) as count FROM bookings
        WHERE room_id = ?
          AND status IN ('pending', 'confirmed')
          AND check_in < ?
          AND check_out > ?
        """,
        (room_id, check_out.isoformat(), check_in.isoformat())
    ).fetchone()
    conn.close()

    if existing["count"] > 0:
        await message.answer(
            "❌ На эти даты номер занят.\n\n"
            "Выберите другую дату заезда:",
            reply_markup=get_calendar(check_in.year, check_in.month)
        )
        await state.set_state(BookingState.choosing_check_in)
        return

    nights = (check_out - check_in).days

    conn = get_connection()
    room = conn.execute(
        "SELECT price_per_night FROM rooms WHERE id = ?",
        (room_id,)
    ).fetchone()
    conn.close()

    price_per_night = room["price_per_night"]

    if room_type == "shared":
        beds_keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="1 место"),
                    KeyboardButton(text="2 места"),
                    KeyboardButton(text="3 места")
                ],
                [KeyboardButton(text="❌ Отмена")]
            ],
            resize_keyboard=True
        )

        await message.answer(
            f"📅 {data['check_in']} → {data['check_out']} | {nights} ноч.\n"
            f"💵 {price_per_night} ₽ за место\n\n"
            f"Сколько мест бронируете? (максимум 3)",
            reply_markup=beds_keyboard
        )
        await state.set_state(BookingState.entering_beds)
    else:
        await state.update_data(beds=1)
        await message.answer(
            f"📅 {data['check_in']} → {data['check_out']} | {nights} ноч.\n"
            f"💵 {price_per_night} ₽ за место\n\n"
            f"Введите ваше имя:"
        )
        await state.set_state(BookingState.entering_name)


# ============================================================
#  БРОНИРОВАНИЕ — Шаг 5: количество мест (общий номер)
# ============================================================

@user_router.message(BookingState.entering_beds, F.text != "❌ Отмена")
async def beds_chosen(message: Message, state: FSMContext):
    text = message.text

    if text == "1 место":
        beds = 1
    elif text == "2 места":
        beds = 2
    elif text == "3 места":
        beds = 3
    else:
        await message.answer("Пожалуйста, выберите количество мест кнопками: 1, 2 или 3.")
        return

    await state.update_data(beds=beds)

    await message.answer(
        f"Бронируете {beds} мест(а) в общем номере.\n\n"
        f"Введите ваше имя:"
    )
    await state.set_state(BookingState.entering_name)


# ============================================================
#  БРОНИРОВАНИЕ — Шаг 6: имя → запрос телефона
# ============================================================

@user_router.message(BookingState.entering_name, F.text != "❌ Отмена")
async def name_entered(message: Message, state: FSMContext):
    name = message.text.strip()

    if len(name) < 2:
        await message.answer("❌ Имя слишком короткое. Введите полное имя (минимум 2 символа):")
        return

    if any(char.isdigit() for char in name):
        await message.answer("❌ Имя не должно содержать цифр. Введите корректное имя:")
        return

    await state.update_data(name=name)

    phone_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Отправить номер телефона", request_contact=True)],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )

    await message.answer(
        f"Имя: {name}\n\n"
        f"Теперь укажите номер телефона.\n"
        f"Нажмите кнопку ниже или введите номер вручную\n"
        f"в формате +7XXXXXXXXXX:",
        reply_markup=phone_keyboard
    )
    await state.set_state(BookingState.entering_phone)


# ============================================================
#  БРОНИРОВАНИЕ — Шаг 7a: телефон через кнопку Telegram
# ============================================================

@user_router.message(BookingState.entering_phone, F.contact)
async def phone_contact_received(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    await process_phone(phone, message, state)


# ============================================================
#  БРОНИРОВАНИЕ — Шаг 7b: телефон текстом
# ============================================================

@user_router.message(BookingState.entering_phone, F.text != "❌ Отмена")
async def phone_text_received(message: Message, state: FSMContext):
    phone = message.text.strip()
    await process_phone(phone, message, state)


# ============================================================
#  БРОНИРОВАНИЕ — Общая функция обработки телефона
# ============================================================

async def process_phone(phone: str, message: Message, state: FSMContext):
    from utils.validators import validate_phone
    from database.db import get_connection

    if not validate_phone(phone):
        await message.answer(
            "❌ Неверный формат телефона.\n"
            "Введите номер в формате +7XXXXXXXXXX (минимум 10 цифр):"
        )
        return

    await state.update_data(phone=phone)
    data = await state.get_data()

    check_in = date.fromisoformat(data["check_in"])
    check_out = date.fromisoformat(data["check_out"])
    nights = (check_out - check_in).days

    conn = get_connection()
    room = conn.execute(
        "SELECT price_per_night FROM rooms WHERE id = ?",
        (data["room_id"],)
    ).fetchone()
    conn.close()

    price_per_night = room["price_per_night"]
    beds = data.get("beds", 1)
    total_price = price_per_night * nights * beds

    confirm_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Подтвердить")],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )

    summary = (
        f"📋 Проверьте данные бронирования\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🛏 Номер: {data['room_name']}\n"
        f"📅 Заезд: {data['check_in']}\n"
        f"📅 Выезд: {data['check_out']}\n"
        f"🌙 Ночей: {nights}\n"
        f"👤 Мест: {beds}\n"
        f"💵 Цена за место: {price_per_night} ₽\n"
        f"💰 Итого к оплате: {total_price} ₽\n\n"
        f"👤 Имя: {data['name']}\n"
        f"📞 Телефон: {phone}\n\n"
        f"Нажмите «Подтвердить» для завершения."
    )

    await message.answer(summary, reply_markup=confirm_keyboard)
    await state.set_state(BookingState.confirming)


# ============================================================
#  БРОНИРОВАНИЕ — Шаг 8: подтверждение → запись в БД
# ============================================================

@user_router.message(BookingState.confirming, F.text == "✅ Подтвердить")
async def booking_confirmed(message: Message, state: FSMContext):
    from database.db import get_connection
    from config import ADMIN_IDS

    data = await state.get_data()

    conn = get_connection()

    user_id = message.from_user.id
    existing_user = conn.execute(
        "SELECT user_id FROM users WHERE user_id = ?", (user_id,)
    ).fetchone()

    if existing_user:
        conn.execute(
            "UPDATE users SET username = ?, full_name = ?, phone = ? WHERE user_id = ?",
            (message.from_user.username, data["name"], data["phone"], user_id)
        )
    else:
        conn.execute(
            "INSERT INTO users (user_id, username, full_name, phone) VALUES (?, ?, ?, ?)",
            (user_id, message.from_user.username, data["name"], data["phone"])
        )

    conn.execute(
        """
        INSERT INTO bookings (user_id, room_id, check_in, check_out, beds, status)
        VALUES (?, ?, ?, ?, ?, 'pending')
        """,
        (user_id, data["room_id"], data["check_in"], data["check_out"], data.get("beds", 1))
    )
    conn.commit()

    booking_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()

    # Уведомление админам
    admin_text = (
        f"🔔 Новая бронь!\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🆔 Бронь №: {booking_id}\n"
        f"🛏 Номер: {data['room_name']}\n"
        f"📅 Заезд: {data['check_in']}\n"
        f"📅 Выезд: {data['check_out']}\n"
        f"👤 Мест: {data.get('beds', 1)}\n"
        f"👤 Гость: {data['name']}\n"
        f"📞 Телефон: {data['phone']}\n"
        f"📩 @{message.from_user.username or 'нет'}\n\n"
        f"Статус: ожидает подтверждения"
    )

    for admin_id in ADMIN_IDS:
        try:
            await message.bot.send_message(admin_id, admin_text)
        except Exception:
            pass

    # Запись в Google Таблицу
    try:
        from utils.sheets import add_booking_to_sheet

        add_booking_to_sheet(
            booking_id=booking_id,
            created_at=datetime.now().strftime("%d.%m.%Y %H:%M"),
            name=data["name"],
            phone=data["phone"],
            room_name=data["room_name"],
            check_in=data["check_in"],
            check_out=data["check_out"],
            beds=str(data.get("beds", 1)),
            status="pending"
        )
    except Exception:
        pass

    await state.clear()
    await message.answer(
        f"✅ Бронирование оформлено!\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Номер брони: {booking_id}\n"
        f"Статус: ожидает подтверждения\n\n"
        f"Мы пришлём уведомление, когда бронь будет подтверждена.\n\n"
        f"Спасибо, что выбрали нас! 🏠",
        reply_markup=get_main_menu()
    )


# ============================================================
#  ❌ ОТМЕНА БРОНИ
# ============================================================

@user_router.message(StateFilter(None), F.text == "❌ Отменить бронь")
async def cancel_booking_start(message: Message):
    from database.db import get_connection

    user_id = message.from_user.id

    conn = get_connection()
    bookings = conn.execute(
        """
        SELECT b.id, b.check_in, b.check_out, b.beds, b.status, r.name as room_name
        FROM bookings b
        JOIN rooms r ON b.room_id = r.id
        WHERE b.user_id = ?
          AND b.status IN ('pending', 'confirmed')
          AND b.check_in >= ?
        ORDER BY b.check_in
        """,
        (user_id, date.today().isoformat())
    ).fetchall()
    conn.close()

    if not bookings:
        await message.answer(
            "У вас нет активных броней.\n\n"
            "Если нужна помощь — свяжитесь с администратором\n"
            "через кнопку 📞 Связь в главном меню.",
            reply_markup=get_main_menu()
        )
        return

    text = "🗑 Ваши активные брони\n"
    text += "━━━━━━━━━━━━━━━━\n\n"
    keyboard_rows = []

    for booking in bookings:
        status_emoji = "🟡" if booking["status"] == "pending" else "🟢"
        text += (
            f"{status_emoji} Бронь №{booking['id']}\n"
            f"   🛏 {booking['room_name']}\n"
            f"   📅 {booking['check_in']} → {booking['check_out']}\n"
            f"   👤 Мест: {booking['beds']}\n\n"
        )
        keyboard_rows.append([
            InlineKeyboardButton(
                text=f"❌ Отменить №{booking['id']}",
                callback_data=f"cancel:{booking['id']}"
            )
        ])

    keyboard_rows.append([
        InlineKeyboardButton(text="↩ Назад", callback_data="cancel:back")
    ])

    cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    text += "Выберите бронь для отмены:"

    await message.answer(text, reply_markup=cancel_keyboard)


@user_router.callback_query(F.data.startswith("cancel:"))
async def cancel_booking_callback(callback: CallbackQuery):
    from database.db import get_connection
    from config import ADMIN_IDS

    payload = callback.data.split(":")[1]

    if payload == "back":
        await callback.message.delete()
        await callback.answer("Возврат в главное меню")
        return

    booking_id = int(payload)
    user_id = callback.from_user.id

    conn = get_connection()
    booking = conn.execute(
        "SELECT id, check_in, status FROM bookings WHERE id = ? AND user_id = ?",
        (booking_id, user_id)
    ).fetchone()

    if not booking:
        conn.close()
        await callback.answer("❌ Бронь не найдена", show_alert=True)
        return

    check_in = datetime.strptime(booking["check_in"], "%Y-%m-%d")
    hours_left = (check_in - datetime.now()).total_seconds() / 3600

    if hours_left < 24:
        conn.close()
        await callback.answer(
            "❌ Отмена невозможна: до заезда осталось менее 24 часов.\n"
            "Свяжитесь с администратором.",
            show_alert=True
        )
        return

    conn.execute("UPDATE bookings SET status = 'cancelled' WHERE id = ?", (booking_id,))
    conn.commit()
    conn.close()

    await callback.message.edit_text(
        f"✅ Бронь №{booking_id} отменена.\n\n"
        f"Будем рады видеть вас снова! 🏠"
    )
    await callback.answer("Бронь отменена ✅")

    for admin_id in ADMIN_IDS:
        try:
            await callback.bot.send_message(
                admin_id,
                f"🗑 Бронь отменена гостем\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"🆔 Бронь №: {booking_id}\n"
                f"👤 Гость: {callback.from_user.full_name}\n"
                f"📩 @{callback.from_user.username or 'нет'}"
            )
        except Exception:
            pass


# ============================================================
#  ⭐ ОТЗЫВЫ
# ============================================================

@user_router.message(StateFilter(None), F.text == "⭐ Отзывы")
async def reviews_main(message: Message):
    from database.db import get_connection

    conn = get_connection()
    reviews = conn.execute(
        """
        SELECT r.rating, r.text, r.created_at, u.full_name
        FROM reviews r
        JOIN users u ON r.user_id = u.user_id
        WHERE r.is_approved = 1
        ORDER BY r.created_at DESC
        LIMIT 5
        """
    ).fetchall()
    conn.close()

    if not reviews:
        text = "⭐ Отзывы\n━━━━━━━━━━━━━━━━\n\nПока нет ни одного отзыва. Будьте первым! ✨"
    else:
        text = "⭐ Отзывы гостей\n━━━━━━━━━━━━━━━━\n\n"
        for rev in reviews:
            stars = "⭐" * rev["rating"]
            text += f"{stars}\n{rev['text']}\n— {rev['full_name']}\n\n"

    review_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Оставить отзыв", callback_data="review:new")],
        [InlineKeyboardButton(text="📖 Все отзывы", callback_data="review:all")]
    ])

    await message.answer(text, reply_markup=review_keyboard)


@user_router.callback_query(F.data == "review:new")
async def review_new(callback: CallbackQuery, state: FSMContext):
    rating_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1 ⭐", callback_data="rating:1"),
            InlineKeyboardButton(text="2 ⭐", callback_data="rating:2"),
            InlineKeyboardButton(text="3 ⭐", callback_data="rating:3"),
            InlineKeyboardButton(text="4 ⭐", callback_data="rating:4"),
            InlineKeyboardButton(text="5 ⭐", callback_data="rating:5"),
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="review:cancel")]
    ])

    await callback.message.delete()
    await callback.message.answer(
        "✍️ Новый отзыв\n━━━━━━━━━━━━━━━━\n\nКак оцениваете проживание?",
        reply_markup=rating_keyboard
    )
    await state.set_state(ReviewState.waiting_for_rating)


@user_router.callback_query(ReviewState.waiting_for_rating, F.data.startswith("rating:"))
async def review_rating_chosen(callback: CallbackQuery, state: FSMContext):
    rating = int(callback.data.split(":")[1])
    await state.update_data(rating=rating)

    cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="review:cancel")]
    ])

    await callback.message.edit_text(
        f"Вы поставили {'⭐' * rating}\n\n"
        f"Напишите текст отзыва\n(или нажмите «Отмена»):",
        reply_markup=cancel_keyboard
    )
    await state.set_state(ReviewState.waiting_for_text)


@user_router.message(ReviewState.waiting_for_text)
async def review_text_received(message: Message, state: FSMContext):
    from database.db import get_connection
    from config import ADMIN_IDS

    text = message.text.strip()

    if len(text) < 3:
        await message.answer("❌ Отзыв слишком короткий. Напишите хотя бы пару слов:")
        return

    data = await state.get_data()
    rating = data["rating"]

    conn = get_connection()

    user_id = message.from_user.id
    existing = conn.execute(
        "SELECT user_id FROM users WHERE user_id = ?", (user_id,)
    ).fetchone()

    if not existing:
        conn.execute(
            "INSERT INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
            (user_id, message.from_user.username, message.from_user.full_name)
        )

    conn.execute(
        "INSERT INTO reviews (user_id, rating, text, is_approved) VALUES (?, ?, ?, 0)",
        (user_id, rating, text)
    )
    conn.commit()
    conn.close()

    await state.clear()
    await message.answer(
        "✅ Спасибо за отзыв!\n\n"
        "Он появится на витрине после проверки администратором. 🏠",
        reply_markup=get_main_menu()
    )

    for admin_id in ADMIN_IDS:
        try:
            await message.bot.send_message(
                admin_id,
                f"⭐ Новый отзыв на модерации\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"Оценка: {'⭐' * rating}\n"
                f"Текст: {text}\n"
                f"👤 {message.from_user.full_name}\n"
                f"📩 @{message.from_user.username or 'нет'}"
            )
        except Exception:
            pass


@user_router.callback_query(F.data == "review:all")
async def review_all(callback: CallbackQuery):
    from database.db import get_connection

    conn = get_connection()
    reviews = conn.execute(
        """
        SELECT r.rating, r.text, r.created_at, u.full_name
        FROM reviews r
        JOIN users u ON r.user_id = u.user_id
        WHERE r.is_approved = 1
        ORDER BY r.created_at DESC
        LIMIT 20
        """
    ).fetchall()
    conn.close()

    if not reviews:
        await callback.answer("Пока нет одобренных отзывов", show_alert=True)
        return

    text = "📖 Все отзывы\n━━━━━━━━━━━━━━━━\n\n"
    for rev in reviews:
        stars = "⭐" * rev["rating"]
        text += f"{stars}\n{rev['text']}\n— {rev['full_name']}\n\n"

    await callback.message.delete()
    await callback.message.answer(text)


@user_router.callback_query(F.data == "review:cancel")
async def review_cancel(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()

    if current_state is not None:
        await state.clear()

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.answer("Отменено")