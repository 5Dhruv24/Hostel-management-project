import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

DB_NAME = "hostel.db"


def init_db():
    """Creates all tables if they don't already exist."""
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

    # Rooms available across hostels. gender = "Male", "Female", or "Any".
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hostel_name TEXT NOT NULL,
            room_number TEXT NOT NULL,
            room_type TEXT NOT NULL,
            gender TEXT NOT NULL,
            capacity INTEGER NOT NULL,
            occupied INTEGER NOT NULL DEFAULT 0
        )
    """)

    # Student hostel applications (dummy sample data for the prototype demo).
    # pref1/pref2/pref3 store hostel names in priority order.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            full_name TEXT NOT NULL,
            gender TEXT NOT NULL,
            course TEXT NOT NULL,
            room_type TEXT NOT NULL,
            pref1_hostel TEXT NOT NULL,
            pref2_hostel TEXT NOT NULL,
            pref3_hostel TEXT NOT NULL,
            priority_note TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            allocated_hostel TEXT,
            allocated_room TEXT,
            reasoning TEXT
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


def seed_sample_data():
    """
    Inserts dummy hostels, rooms, and student applications for demo purposes,
    but only if the tables are currently empty (so this is safe to call every
    time the app starts without creating duplicates).
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM rooms")
    if cursor.fetchone()[0] == 0:
        rooms = [
            ("Hostel A", "101", "Double", "Male", 2, 0),
            ("Hostel A", "102", "Double", "Male", 2, 2),   # already full
            ("Hostel A", "103", "Single", "Male", 1, 0),
            ("Hostel B", "201", "Double", "Female", 2, 0),
            ("Hostel B", "202", "Triple", "Female", 3, 3), # already full
            ("Hostel B", "203", "Single", "Female", 1, 0),
            ("Hostel C", "301", "Double", "Any", 2, 1),    # 1 seat left
        ]
        cursor.executemany(
            "INSERT INTO rooms (hostel_name, room_number, room_type, gender, capacity, occupied) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            rooms
        )

    cursor.execute("SELECT COUNT(*) FROM applications")
    if cursor.fetchone()[0] == 0:
        applications = [
            ("student1", "Aarav Sharma", "Male", "B.Tech CSE", "Double",
             "Hostel A", "Hostel C", "Hostel A", "General category"),
            ("student2", "Priya Nair", "Female", "B.Tech ECE", "Single",
             "Hostel B", "Hostel B", "Hostel B", "General category"),
            ("student3", "Rohan Gupta", "Male", "B.Tech ME", "Double",
             "Hostel A", "Hostel A", "Hostel C", "Distance > 50km (priority)"),
            ("student4", "Sneha Iyer", "Female", "B.Tech CSE", "Triple",
             "Hostel B", "Hostel B", "Hostel B", "General category"),
            ("student5", "Karan Verma", "Male", "B.Tech CSE", "Single",
             "Hostel A", "Hostel A", "Hostel A", "General category"),
        ]
        cursor.executemany(
            "INSERT INTO applications "
            "(user_id, full_name, gender, course, room_type, pref1_hostel, pref2_hostel, pref3_hostel, priority_note) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            applications
        )

    conn.commit()
    conn.close()


def get_all_applications():
    """Returns every application, admin-only view."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM applications ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_application_for_user(user_id):
    """Returns only this specific student's own application, or None."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM applications WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def run_allocation():
    """
    The rule-based allocation engine.

    For every Pending application, tries the student's 3 hostel preferences
    in order. For each preference, looks for a room in that hostel matching
    the student's required gender and room type, with a free seat. Assigns
    the first match found. If none of the 3 preferences have space, the
    student is marked Waitlisted instead.

    A human-readable "reasoning" string is stored for every outcome, so the
    student can later see exactly why they got (or didn't get) their room.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM applications WHERE status = 'Pending'")
    pending = cursor.fetchall()

    for app in pending:
        allocated = False

        preferences = [
            (1, app["pref1_hostel"]),
            (2, app["pref2_hostel"]),
            (3, app["pref3_hostel"]),
        ]

        for rank, hostel_name in preferences:
            cursor.execute("""
                SELECT * FROM rooms
                WHERE hostel_name = ?
                  AND room_type = ?
                  AND (gender = ? OR gender = 'Any')
                  AND occupied < capacity
                ORDER BY id
                LIMIT 1
            """, (hostel_name, app["room_type"], app["gender"]))

            room = cursor.fetchone()

            if room:
                # Assign this room: increase its occupied count by 1
                cursor.execute(
                    "UPDATE rooms SET occupied = occupied + 1 WHERE id = ?",
                    (room["id"],)
                )

                reasoning = (
                    f"Allocated Room {room['room_number']} in {room['hostel_name']} "
                    f"because it was your preference #{rank} ({hostel_name}), "
                    f"it matched your required room type ({app['room_type']}) and gender, "
                    f"and had an available seat at the time of allocation. "
                    f"Priority note considered: {app['priority_note']}."
                )

                cursor.execute("""
                    UPDATE applications
                    SET status = 'Allocated',
                        allocated_hostel = ?,
                        allocated_room = ?,
                        reasoning = ?
                    WHERE id = ?
                """, (room["hostel_name"], room["room_number"], reasoning, app["id"]))

                allocated = True
                break

        if not allocated:
            reasoning = (
                f"Not allocated in this round. All 3 of your preferences "
                f"({app['pref1_hostel']}, {app['pref2_hostel']}, {app['pref3_hostel']}) "
                f"had no available {app['room_type']} seats matching your gender at the time "
                f"of allocation. You have been placed on the waiting list and will be "
                f"allocated automatically when a matching seat becomes free."
            )
            cursor.execute("""
                UPDATE applications
                SET status = 'Waitlisted', reasoning = ?
                WHERE id = ?
            """, (reasoning, app["id"]))

    conn.commit()
    conn.close()