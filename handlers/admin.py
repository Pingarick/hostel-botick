from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import ADMIN_IDS

admin_router = Router()


# ============================================================
#  ПРОВЕРКА АДМИНА
# ============================================================

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ============================================================
#  FSM ДЛЯ АДМИНКИ
# ============================================================

class AdminState(StatesGroup):
    waiting_for_close_room = State()
    waiting_for_close_check_in = State()
    waiting_for_close_check_out = State()
    waiting_for_broadcast = State()


# ============================================================
#  КЛАВИАТУРЫ АДМИНКИ
# ============================================================

def get_admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Все брони", callback_data="admin:bookings")],
        [
            InlineKeyboardButton(text="✅ Подтвердить бронь", callback_data="admin:confirm"),
            InlineKeyboardButton(text="🚫 Закрыть даты", callback_data="admin:close_dates"),
        ],
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats"),
            InlineKeyboardButton(text="⭐ Модерация отзывов", callback_data="admin:reviews"),
        ],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin:broadcast")],
    ])


def back_to_admin() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↩ Назад", callback_data="admin:back")]
    ])


# ============================================================
#  /admin — ВХОД
# ============================================================

@admin_router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("🚫 У вас нет доступа к админ-панели")
        return

    await message.answer(
        "🔧 <b>Админ-панель</b>\n\nВыберите действие:",
        reply_markup=get_admin_keyboard()
    )


@admin_router.callback_query(F.data == "admin:back")
async def admin_back(callback: CallbackQuery):
    await callback.message.edit_text(
        "🔧 <b>Админ-панель</b>\n\nВыберите действие:",
        reply_markup=get_admin_keyboard()
    )


# ============================================================
#  📋 ВСЕ БРОНИ
# ============================================================

@admin_router.callback_query(F.data == "admin:bookings")
async def admin_bookings(callback: CallbackQuery):
    from database.db import get_connection

    conn = get_connection()
    bookings = conn.execute(
        """
        SELECT b.id, b.check_in, b.check_out, b.beds, b.status, b.created_at,
               r.name as room_name, u.full_name, u.phone, u.username
        FROM bookings b
        JOIN rooms r ON b.room_id = r.id
        JOIN users u ON b.user_id = u.user_id
        ORDER BY b.status, b.check_in DESC
        LIMIT 30
        """
    ).fetchall()
    conn.close()

    if not bookings:
        await callback.answer("Броней пока нет", show_alert=True)
        return

    pending = []
    confirmed = []
    cancelled = []

    for b in bookings:
        entry = (
            f"🆔 <b>№{b['id']}</b> | {b['room_name']}\n"
            f"📅 {b['check_in']} → {b['check_out']} | 👤 {b['beds']} мест\n"
            f"👤 {b['full_name']} | 📞 {b['phone']}\n"
        )
        if b["status"] == "pending":
            pending.append(entry)
        elif b["status"] == "confirmed":
            confirmed.append(entry)
        else:
            cancelled.append(entry)

    text = "📋 <b>Все брони:</b>\n\n"

    if pending:
        text += "🟡 <b>Ожидают подтверждения:</b>\n" + "\n".join(pending) + "\n"
    if confirmed:
        text += "🟢 <b>Подтверждены:</b>\n" + "\n".join(confirmed) + "\n"
    if cancelled:
        text += "🔴 <b>Отменены:</b>\n" + "\n".join(cancelled) + "\n"

    await callback.message.edit_text(text, reply_markup=back_to_admin())


# ============================================================
#  ✅ ПОДТВЕРДИТЬ БРОНЬ
# ============================================================

@admin_router.callback_query(F.data == "admin:confirm")
async def admin_confirm_list(callback: CallbackQuery):
    from database.db import get_connection

    conn = get_connection()
    bookings = conn.execute(
        """
        SELECT b.id, b.check_in, b.check_out, r.name as room_name, u.full_name
        FROM bookings b
        JOIN rooms r ON b.room_id = r.id
        JOIN users u ON b.user_id = u.user_id
        WHERE b.status = 'pending'
        ORDER BY b.check_in
        """
    ).fetchall()
    conn.close()

    if not bookings:
        await callback.answer("Нет броней, ожидающих подтверждения", show_alert=True)
        return

    text = "✅ <b>Выберите бронь для подтверждения:</b>\n\n"
    keyboard_rows = []

    for b in bookings:
        text += (
            f"🆔 <b>№{b['id']}</b> | {b['room_name']}\n"
            f"📅 {b['check_in']} → {b['check_out']}\n"
            f"👤 {b['full_name']}\n\n"
        )
        keyboard_rows.append([
            InlineKeyboardButton(
                text=f"✅ Подтвердить №{b['id']}",
                callback_data=f"confirm:{b['id']}"
            )
        ])

    keyboard_rows.append([InlineKeyboardButton(text="↩ Назад", callback_data="admin:back")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)

    await callback.message.edit_text(text, reply_markup=keyboard)


@admin_router.callback_query(F.data.startswith("confirm:"))
async def admin_confirm_booking(callback: CallbackQuery):
    from database.db import get_connection

    booking_id = int(callback.data.split(":")[1])

    conn = get_connection()
    booking = conn.execute(
        "SELECT id, user_id, check_in, check_out FROM bookings WHERE id = ? AND status = 'pending'",
        (booking_id,)
    ).fetchone()

    if not booking:
        conn.close()
        await callback.answer("Бронь уже обработана или не найдена", show_alert=True)
        return

    conn.execute("UPDATE bookings SET status = 'confirmed' WHERE id = ?", (booking_id,))
    conn.commit()
    conn.close()

    await callback.message.edit_text(
        f"✅ <b>Бронь №{booking_id} подтверждена!</b>\n\n"
        f"Гость получит уведомление.",
        reply_markup=back_to_admin()
    )

    try:
        await callback.bot.send_message(
            booking["user_id"],
            f"✅ <b>Бронь №{booking_id} подтверждена!</b>\n\n"
            f"📅 Заезд: {booking['check_in']}\n"
            f"📅 Выезд: {booking['check_out']}\n\n"
            f"Ждём вас! 🏠\n"
            f"Заезд с 14:00."
        )
    except Exception:
        pass

    await callback.answer("Бронь подтверждена ✅")


# ============================================================
#  🚫 ЗАКРЫТЬ ДАТЫ
# ============================================================

@admin_router.callback_query(F.data == "admin:close_dates")
async def admin_close_dates_start(callback: CallbackQuery, state: FSMContext):
    from database.db import get_connection

    conn = get_connection()
    rooms = conn.execute("SELECT id, name FROM rooms").fetchall()
    conn.close()

    keyboard_rows = []
    for room in rooms:
        keyboard_rows.append([
            InlineKeyboardButton(text=room["name"], callback_data=f"close_room:{room['id']}")
        ])
    keyboard_rows.append([InlineKeyboardButton(text="↩ Назад", callback_data="admin:back")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)

    await callback.message.edit_text(
        "🚫 <b>Закрытие дат</b>\n\nВыберите номер:",
        reply_markup=keyboard
    )
    await state.set_state(AdminState.waiting_for_close_room)


@admin_router.callback_query(AdminState.waiting_for_close_room, F.data.startswith("close_room:"))
async def admin_close_dates_room(callback: CallbackQuery, state: FSMContext):
    room_id = int(callback.data.split(":")[1])
    await state.update_data(close_room_id=room_id)

    await callback.message.edit_text(
        "Введите дату начала закрытия в формате ДД.ММ.ГГГГ\n"
        "Например: 20.12.2026",
        reply_markup=back_to_admin()
    )
    await state.set_state(AdminState.waiting_for_close_check_in)


@admin_router.message(AdminState.waiting_for_close_check_in)
async def admin_close_dates_check_in(message: Message, state: FSMContext):
    from datetime import datetime

    try:
        date_in = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
    except ValueError:
        await message.answer("❌ Неверный формат. Введите дату как ДД.ММ.ГГГГ")
        return

    await state.update_data(close_check_in=date_in.isoformat())
    await message.answer("Введите дату окончания закрытия (ДД.ММ.ГГГГ):")
    await state.set_state(AdminState.waiting_for_close_check_out)


@admin_router.message(AdminState.waiting_for_close_check_out)
async def admin_close_dates_finish(message: Message, state: FSMContext):
    from datetime import datetime
    from database.db import get_connection

    try:
        date_out = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
    except ValueError:
        await message.answer("❌ Неверный формат. Введите дату как ДД.ММ.ГГГГ")
        return

    data = await state.get_data()
    room_id = data["close_room_id"]
    check_in = data["close_check_in"]

    conn = get_connection()
    conn.execute(
        """
        INSERT INTO bookings (user_id, room_id, check_in, check_out, beds, status)
        VALUES (?, ?, ?, ?, 99, 'confirmed')
        """,
        (ADMIN_IDS[0], room_id, check_in, date_out.isoformat())
    )
    conn.commit()
    conn.close()

    await state.clear()
    await message.answer(
        f"🚫 Даты закрыты: {check_in} → {date_out.isoformat()}\n\n"
        f"Бронь №99 мест — техническая блокировка.",
        reply_markup=get_admin_keyboard()
    )


# ============================================================
#  📊 СТАТИСТИКА
# ============================================================

@admin_router.callback_query(F.data == "admin:stats")
async def admin_stats(callback: CallbackQuery):
    from database.db import get_connection
    from datetime import date, timedelta

    conn = get_connection()

    total = conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]
    confirmed = conn.execute("SELECT COUNT(*) FROM bookings WHERE status = 'confirmed'").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM bookings WHERE status = 'pending'").fetchone()[0]
    cancelled = conn.execute("SELECT COUNT(*) FROM bookings WHERE status = 'cancelled'").fetchone()[0]

    month_ago = (date.today() - timedelta(days=30)).isoformat()
    month_bookings = conn.execute(
        "SELECT COUNT(*) FROM bookings WHERE created_at >= ?",
        (month_ago,)
    ).fetchone()[0]

    today = date.today().isoformat()
    week_later = (date.today() + timedelta(days=7)).isoformat()

    rooms_load = conn.execute(
        """
        SELECT r.name, COUNT(b.id) as count
        FROM rooms r
        LEFT JOIN bookings b ON r.id = b.room_id
            AND b.status IN ('pending', 'confirmed')
            AND b.check_in < ?
            AND b.check_out > ?
        GROUP BY r.id
        """,
        (week_later, today)
    ).fetchall()

    conn.close()

    text = (
        f"📊 <b>Статистика:</b>\n\n"
        f"📋 <b>Всего броней:</b> {total}\n"
        f"🟢 Подтверждено: {confirmed}\n"
        f"🟡 Ожидают: {pending}\n"
        f"🔴 Отменено: {cancelled}\n\n"
        f"📅 <b>За последние 30 дней:</b> {month_bookings} броней\n\n"
        f"📅 <b>Загрузка на ближайшие 7 дней:</b>\n"
    )

    for room in rooms_load:
        text += f"• {room['name']}: {room['count']} броней\n"

    await callback.message.edit_text(text, reply_markup=back_to_admin())


# ============================================================
#  ⭐ МОДЕРАЦИЯ ОТЗЫВОВ
# ============================================================

@admin_router.callback_query(F.data == "admin:reviews")
async def admin_reviews_list(callback: CallbackQuery):
    from database.db import get_connection

    conn = get_connection()
    reviews = conn.execute(
        """
        SELECT r.id, r.rating, r.text, r.created_at, u.full_name
        FROM reviews r
        JOIN users u ON r.user_id = u.user_id
        WHERE r.is_approved = 0
        ORDER BY r.created_at DESC
        """
    ).fetchall()
    conn.close()

    if not reviews:
        await callback.answer("Нет отзывов на модерации", show_alert=True)
        return

    text = "⭐ <b>Отзывы на модерации:</b>\n\n"
    keyboard_rows = []

    for rev in reviews:
        stars = "⭐" * rev["rating"]
        text += f"{stars} | {rev['full_name']}\n<i>{rev['text']}</i>\n\n"
        keyboard_rows.append([
            InlineKeyboardButton(
                text=f"✅ Одобрить отзыв №{rev['id']}",
                callback_data=f"approve_review:{rev['id']}"
            ),
            InlineKeyboardButton(
                text=f"🗑 Удалить",
                callback_data=f"delete_review:{rev['id']}"
            )
        ])

    keyboard_rows.append([InlineKeyboardButton(text="↩ Назад", callback_data="admin:back")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)

    await callback.message.edit_text(text, reply_markup=keyboard)


@admin_router.callback_query(F.data.startswith("approve_review:"))
async def admin_approve_review(callback: CallbackQuery):
    from database.db import get_connection

    review_id = int(callback.data.split(":")[1])

    conn = get_connection()
    conn.execute("UPDATE reviews SET is_approved = 1 WHERE id = ?", (review_id,))
    conn.commit()
    conn.close()

    await callback.answer("Отзыв одобрен ✅")
    await admin_reviews_list(callback)


@admin_router.callback_query(F.data.startswith("delete_review:"))
async def admin_delete_review(callback: CallbackQuery):
    from database.db import get_connection

    review_id = int(callback.data.split(":")[1])

    conn = get_connection()
    conn.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
    conn.commit()
    conn.close()

    await callback.answer("Отзыв удалён 🗑")
    await admin_reviews_list(callback)


# ============================================================
#  📢 РАССЫЛКА
# ============================================================

@admin_router.callback_query(F.data == "admin:broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📢 <b>Рассылка</b>\n\n"
        "Введите текст сообщения, которое будет отправлено всем пользователям.\n"
        "Для отмены нажмите кнопку «Назад».",
        reply_markup=back_to_admin()
    )
    await state.set_state(AdminState.waiting_for_broadcast)


@admin_router.message(AdminState.waiting_for_broadcast)
async def admin_broadcast_send(message: Message, state: FSMContext):
    from database.db import get_connection

    conn = get_connection()
    users = conn.execute("SELECT user_id FROM users").fetchall()
    conn.close()

    sent = 0
    failed = 0

    for user in users:
        try:
            await message.bot.send_message(user["user_id"], message.text)
            sent += 1
        except Exception:
            failed += 1

    await state.clear()
    await message.answer(
        f"📢 <b>Рассылка завершена</b>\n\n"
        f"✅ Отправлено: {sent}\n"
        f"❌ Не доставлено: {failed}",
        reply_markup=get_admin_keyboard()
    )