import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

admin_ids_str = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(id_str) for id_str in admin_ids_str.split(",") if id_str]

HOSTEL_NAME = os.getenv("HOSTEL_NAME", "Хостел")

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "")