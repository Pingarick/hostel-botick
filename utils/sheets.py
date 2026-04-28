import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import SPREADSHEET_ID
import logging


def get_sheet():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        "credentials.json", scope
    )

    client = gspread.authorize(credentials)
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1
    return sheet


def add_booking_to_sheet(booking_id, created_at, name, phone, room_name,
                         check_in, check_out, beds, status):
    if not SPREADSHEET_ID:
        logging.warning("SPREADSHEET_ID не указан, пропускаю запись в таблицу")
        return

    try:
        sheet = get_sheet()

        row = [
            str(booking_id),
            created_at,
            name,
            phone,
            room_name,
            check_in,
            check_out,
            str(beds),
            status
        ]

        sheet.append_row(row)
        logging.info(f"Бронь №{booking_id} добавлена в Google Таблицу")

    except Exception as e:
        logging.error(f"Ошибка записи в Google Таблицу: {e}")