import sqlite3

DB_PATH = "data/hostel.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Пользователи (гости)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Номера
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            name TEXT NOT NULL,
            total_beds INTEGER,
            price_per_night INTEGER
        )
    """)

    # Бронирования
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            room_id INTEGER,
            check_in DATE NOT NULL,
            check_out DATE NOT NULL,
            beds INTEGER DEFAULT 1,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (room_id) REFERENCES rooms(id)
        )
    """)

    # Отзывы
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            rating INTEGER CHECK(rating >= 1 AND rating <= 5),
            text TEXT,
            is_approved INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    # Заполняем номера при первом запуске
    cursor.execute("SELECT COUNT(*) FROM rooms")
    count = cursor.fetchone()[0]

    if count == 0:
        rooms_data = [
            ("shared", "Общий номер", 8, 790),
            ("female", "Женский номер", 6, 850),
            ("private", "Приватный номер", 2, 2500),
        ]
        cursor.executemany(
            "INSERT INTO rooms (type, name, total_beds, price_per_night) VALUES (?, ?, ?, ?)",
            rooms_data
        )

    conn.commit()
    conn.close()