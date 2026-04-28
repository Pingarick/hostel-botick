import asyncio
from datetime import date, timedelta
from database.db import get_connection


async def check_reminders(bot):
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    conn = get_connection()
    bookings = conn.execute(
        """
        SELECT b.id, b.user_id, b.check_in, b.check_out, r.name as room_name
        FROM bookings b
        JOIN rooms r ON b.room_id = r.id
        WHERE b.status = 'confirmed'
          AND b.check_in = ?
        """,
        (tomorrow,)
    ).fetchall()
    conn.close()

    for booking in bookings:
        user_id = booking["user_id"]
        text = (
            f"🔔 <b>Напоминание!</b>\n\n"
            f"Завтра у вас заезд в хостеле!\n\n"
            f"🛏 Номер: <b>{booking['room_name']}</b>\n"
            f"📅 Заезд: <b>{booking['check_in']}</b> (с 14:00)\n"
            f"📅 Выезд: <b>{booking['check_out']}</b> (до 12:00)\n\n"
            f"Хорошей дороги и до встречи! 🏠"
        )

        try:
            await bot.send_message(user_id, text)
        except Exception:
            pass


async def reminder_loop(bot, interval_hours: int = 1):
    while True:
        await check_reminders(bot)
        await asyncio.sleep(interval_hours * 3600)