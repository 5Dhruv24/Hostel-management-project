import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

DB_NAME = "hostel.db"


def init_db():
    """Creates the users table if it doesn't already exist."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def create_user(user_id, password, role):
    """Adds a new user. Returns True if successful, False if user_id already exists."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    password_hash = generate_password_hash(password)
    try:
        cursor.execute(
            "INSERT INTO users (user_id, password_hash, role) VALUES (?, ?, ?)",
            (user_id, password_hash, role)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # This happens if user_id already exists (we set it as UNIQUE above)
        return False
    finally:
        conn.close()


def verify_user(user_id, password, role):
    """Checks if user_id + password + role match a record. Returns True/False."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT password_hash FROM users WHERE user_id = ? AND role = ?",
        (user_id, role)
    )
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return False

    stored_hash = row[0]
    return check_password_hash(stored_hash, password)