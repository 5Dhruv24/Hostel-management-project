import sqlite3
import random
from datetime import datetime
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
    # priority_score is a number used to rank the waiting list (higher = higher priority).
    # applied_at is used as a tie-breaker when two students have the same score.
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
            priority_score INTEGER NOT NULL DEFAULT 50,
            applied_at TEXT NOT NULL,
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


# --- Priority scoring ---
# In a real system, this score would come from official eligibility rules
# (distance from home, category, year, etc). For this prototype, we convert
# the same priority_note text students already fill in into a number, so the
# whole system (allocation AND waiting list ranking) uses ONE consistent score.
PRIORITY_SCORE_MAP = {
    "Distance > 50km (priority)": 90,
    "Sports quota": 85,
    "Differently-abled": 95,
    "Economically weaker section": 80,
    "General category": 60,
}


def compute_priority_score(priority_note):
    return PRIORITY_SCORE_MAP.get(priority_note, 60)


def seed_sample_data():
    """
    Inserts dummy hostels, rooms, and ~30 student applications for demo
    purposes, but only if the tables are currently empty (safe to call every
    time the app starts, won't create duplicates).

    Total room capacity is intentionally kept around 20 beds, with ~30
    applications, so a realistic waiting list naturally forms — matching a
    real hostel scenario where demand exceeds supply.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM rooms")
    if cursor.fetchone()[0] == 0:
        rooms = [
            ("Hostel A", "101", "Double", "Male", 2, 0),
            ("Hostel A", "102", "Double", "Male", 2, 0),
            ("Hostel A", "103", "Single", "Male", 1, 0),
            ("Hostel A", "104", "Double", "Male", 2, 0),
            ("Hostel B", "201", "Double", "Female", 2, 0),
            ("Hostel B", "202", "Triple", "Female", 3, 0),
            ("Hostel B", "203", "Single", "Female", 1, 0),
            ("Hostel B", "204", "Double", "Female", 2, 0),
            ("Hostel C", "301", "Double", "Any", 2, 0),
            ("Hostel C", "302", "Triple", "Any", 3, 0),
        ]
        # Total capacity here = 2+2+1+2+2+3+1+2+2+3 = 20 beds
        cursor.executemany(
            "INSERT INTO rooms (hostel_name, room_number, room_type, gender, capacity, occupied) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            rooms
        )

    cursor.execute("SELECT COUNT(*) FROM applications")
    if cursor.fetchone()[0] == 0:
        first_names_m = ["Aarav", "Rohan", "Karan", "Aditya", "Vihaan", "Arjun", "Dev", "Kabir", "Reyansh", "Yash",
                          "Ishaan", "Sai", "Advait", "Vivaan", "Ayaan"]
        first_names_f = ["Priya", "Sneha", "Ananya", "Diya", "Isha", "Riya", "Meera", "Kavya", "Anika", "Tara",
                          "Nisha", "Pooja", "Aditi", "Sana", "Zara"]
        last_names = ["Sharma", "Nair", "Gupta", "Iyer", "Verma", "Reddy", "Rao", "Kapoor", "Malhotra", "Bose",
                      "Chatterjee", "Joshi", "Menon", "Pillai", "Singh"]
        courses = ["B.Tech CSE", "B.Tech ECE", "B.Tech ME", "B.Tech Civil", "B.Tech IT"]
        priority_notes = list(PRIORITY_SCORE_MAP.keys())

        random.seed(42)  # fixed seed so the demo data is the same every time
        applications = []

        for i in range(1, 31):  # student1 .. student30
            is_male = (i % 2 == 1)
            gender = "Male" if is_male else "Female"
            first = random.choice(first_names_m if is_male else first_names_f)
            last = random.choice(last_names)
            full_name = f"{first} {last}"
            course = random.choice(courses)
            room_type = random.choice(["Single", "Double", "Triple"])

            hostels_for_gender = ["Hostel A", "Hostel C"] if is_male else ["Hostel B", "Hostel C"]
            prefs = random.sample(hostels_for_gender, k=len(hostels_for_gender))
            while len(prefs) < 3:
                prefs.append(random.choice(hostels_for_gender))

            # Weighted so most students are "General category" like a real applicant pool,
            # with a smaller number of higher-priority cases
            note = random.choices(
                priority_notes,
                weights=[10, 8, 5, 8, 40],  # roughly matches PRIORITY_SCORE_MAP order above
                k=1
            )[0]
            score = compute_priority_score(note)

            applied_at = f"2026-08-{10 + (i % 10):02d} {8 + (i % 10)}:00:00"

            applications.append((
                f"student{i}", full_name, gender, course, room_type,
                prefs[0], prefs[1], prefs[2], note, score, applied_at
            ))

        cursor.executemany(
            "INSERT INTO applications "
            "(user_id, full_name, gender, course, room_type, pref1_hostel, pref2_hostel, pref3_hostel, "
            "priority_note, priority_score, applied_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            applications
        )

    conn.commit()
    conn.close()


def get_all_applications():
    """Returns every application, admin-only view, highest priority first."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM applications ORDER BY priority_score DESC, applied_at ASC")
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


def get_room_counts():
    """Returns overall room stats for the admin dashboard."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COALESCE(SUM(capacity),0), COALESCE(SUM(occupied),0) FROM rooms")
    total, occupied = cursor.fetchone()
    conn.close()
    return {"total": total, "occupied": occupied, "available": total - occupied}


def get_waiting_list():
    """
    Returns the LIVE waiting list: every application with status='Waiting',
    ordered by priority_score (highest first), then applied_at as a
    tie-breaker. Position is calculated fresh from this order every time,
    never stored — so cancellations/withdrawals instantly re-rank everyone
    with no manual renumbering needed.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM applications
        WHERE status = 'Waiting'
        ORDER BY priority_score DESC, applied_at ASC
    """)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()

    for index, row in enumerate(rows):
        row["position"] = index + 1

    return rows


def get_waiting_position_for_user(user_id):
    """
    Returns (position, total_waiting) for one student if they are currently
    on the active waiting list, otherwise None.
    """
    waiting_list = get_waiting_list()
    for row in waiting_list:
        if row["user_id"] == user_id:
            return row["position"], len(waiting_list)
    return None


def _find_room_for(cursor, app_row):
    """
    Internal helper: given an application (sqlite3.Row or dict), searches the
    student's 3 hostel preferences in order for a room matching room_type +
    gender with a free seat. Returns (room, preference_rank) or (None, None).
    """
    preferences = [
        (1, app_row["pref1_hostel"]),
        (2, app_row["pref2_hostel"]),
        (3, app_row["pref3_hostel"]),
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
        """, (hostel_name, app_row["room_type"], app_row["gender"]))
        room = cursor.fetchone()
        if room:
            return room, rank

    return None, None


def run_allocation():
    """
    The rule-based allocation engine.

    Processes every Pending application in priority order (highest
    priority_score first, applied_at as tie-breaker) — so higher-priority
    students get first pick of available rooms. For each student, tries
    their 3 hostel preferences in order and assigns the first matching room
    with a free seat. If none of the 3 preferences have space, the student
    is placed on the waiting list instead.

    A human-readable "reasoning" string is stored either way, so the student
    can see exactly why they got (or didn't get) a room.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM applications
        WHERE status = 'Pending'
        ORDER BY priority_score DESC, applied_at ASC
    """)
    pending = cursor.fetchall()

    for app in pending:
        room, rank = _find_room_for(cursor, app)

        if room:
            cursor.execute("UPDATE rooms SET occupied = occupied + 1 WHERE id = ?", (room["id"],))

            reasoning = (
                f"Allocated Room {room['room_number']} in {room['hostel_name']} "
                f"because it was your preference #{rank} ({app[f'pref{rank}_hostel']}), "
                f"it matched your required room type ({app['room_type']}) and gender, "
                f"and had an available seat at the time of allocation. "
                f"Priority category: {app['priority_note']} (score {app['priority_score']})."
            )

            cursor.execute("""
                UPDATE applications
                SET status = 'Allocated', allocated_hostel = ?, allocated_room = ?, reasoning = ?
                WHERE id = ?
            """, (room["hostel_name"], room["room_number"], reasoning, app["id"]))
        else:
            reasoning = (
                f"Not allocated in this round. All 3 of your preferences "
                f"({app['pref1_hostel']}, {app['pref2_hostel']}, {app['pref3_hostel']}) "
                f"had no available {app['room_type']} seats matching your gender at the time "
                f"of allocation. You have been placed on the waiting list, ranked by your "
                f"priority category: {app['priority_note']} (score {app['priority_score']}). "
                f"You will be allocated automatically if a matching seat becomes free."
            )
            cursor.execute("""
                UPDATE applications SET status = 'Waiting', reasoning = ? WHERE id = ?
            """, (reasoning, app["id"]))

    conn.commit()
    conn.close()


def get_fairness_stats():
    """
    Computes transparency/fairness metrics from the current allocation
    result, so admins (and, on a demo, judges) can verify the algorithm
    isn't biased toward any particular gender or hostel preference — only
    the priority_score already used by the allocation engine.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Average priority score: allocated vs waiting.
    # If the algorithm is fair, allocated students should have a
    # meaningfully higher average score than those still waiting.
    cursor.execute("SELECT AVG(priority_score) FROM applications WHERE status = 'Allocated'")
    avg_allocated = cursor.fetchone()[0] or 0

    cursor.execute("SELECT AVG(priority_score) FROM applications WHERE status = 'Waiting'")
    avg_waiting = cursor.fetchone()[0] or 0

    # Allocation rate by gender - should be roughly similar between
    # genders if the algorithm isn't favoring one over the other.
    cursor.execute("""
        SELECT gender,
               COUNT(*) AS total,
               SUM(CASE WHEN status = 'Allocated' THEN 1 ELSE 0 END) AS allocated
        FROM applications
        WHERE status IN ('Allocated', 'Waiting')
        GROUP BY gender
    """)
    by_gender = []
    for row in cursor.fetchall():
        rate = round((row["allocated"] / row["total"]) * 100) if row["total"] else 0
        by_gender.append({"label": row["gender"], "total": row["total"], "allocated": row["allocated"], "rate": rate})

    # Allocation rate by priority category - shows higher-priority
    # categories (e.g. distance, accessibility) do in fact get allocated
    # at a higher rate, proving the priority rules are actually applied.
    cursor.execute("""
        SELECT priority_note,
               COUNT(*) AS total,
               SUM(CASE WHEN status = 'Allocated' THEN 1 ELSE 0 END) AS allocated
        FROM applications
        WHERE status IN ('Allocated', 'Waiting')
        GROUP BY priority_note
        ORDER BY AVG(priority_score) DESC
    """)
    by_category = []
    for row in cursor.fetchall():
        rate = round((row["allocated"] / row["total"]) * 100) if row["total"] else 0
        by_category.append({"label": row["priority_note"], "total": row["total"], "allocated": row["allocated"], "rate": rate})

    conn.close()

    return {
        "avg_allocated": round(avg_allocated, 1),
        "avg_waiting": round(avg_waiting, 1),
        "by_gender": by_gender,
        "by_category": by_category,
    }


def withdraw_application(user_id):
    """
    Called when a student withdraws/cancels their own application.

    - If they were Waiting or Pending: they're simply marked Cancelled and
      disappear from the live waiting list (which is recalculated fresh
      every time it's read, so everyone below them moves up automatically).

    - If they were already Allocated: their room seat is freed up, marked
      Cancelled, and the system immediately checks the waiting list for the
      next eligible student who listed that hostel as a preference and
      matches the room's gender/type — allocating it to them right away.

    Returns a short status message describing what happened.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM applications WHERE user_id = ?", (user_id,))
    app = cursor.fetchone()

    if not app:
        conn.close()
        return "No application found."

    if app["status"] == "Allocated":
        # Free up the room they were occupying
        cursor.execute("""
            SELECT * FROM rooms WHERE hostel_name = ? AND room_number = ?
        """, (app["allocated_hostel"], app["allocated_room"]))
        room = cursor.fetchone()

        cursor.execute(
            "UPDATE applications SET status = 'Cancelled', reasoning = ? WHERE id = ?",
            ("You withdrew your allocated hostel room.", app["id"])
        )

        if room:
            cursor.execute("UPDATE rooms SET occupied = occupied - 1 WHERE id = ?", (room["id"],))

            # Now find the next eligible waiting student for THIS specific vacated room:
            # must match gender/room_type, and must have listed this hostel as a preference.
            cursor.execute("""
                SELECT * FROM applications
                WHERE status = 'Waiting'
                  AND room_type = ?
                  AND (gender = ? OR ? = 'Any')
                  AND (? = pref1_hostel OR ? = pref2_hostel OR ? = pref3_hostel)
                ORDER BY priority_score DESC, applied_at ASC
                LIMIT 1
            """, (
                room["room_type"], room["gender"], room["gender"],
                room["hostel_name"], room["hostel_name"], room["hostel_name"]
            ))
            next_student = cursor.fetchone()

            if next_student:
                cursor.execute("UPDATE rooms SET occupied = occupied + 1 WHERE id = ?", (room["id"],))

                rank = None
                for r in (1, 2, 3):
                    if next_student[f"pref{r}_hostel"] == room["hostel_name"]:
                        rank = r
                        break

                reasoning = (
                    f"Allocated Room {room['room_number']} in {room['hostel_name']} because a seat "
                    f"became available after another student withdrew, and you were the highest-priority "
                    f"eligible student on the waiting list whose preference #{rank} matched this hostel. "
                    f"Priority category: {next_student['priority_note']} (score {next_student['priority_score']})."
                )

                cursor.execute("""
                    UPDATE applications
                    SET status = 'Allocated', allocated_hostel = ?, allocated_room = ?, reasoning = ?
                    WHERE id = ?
                """, (room["hostel_name"], room["room_number"], reasoning, next_student["id"]))

        conn.commit()
        conn.close()
        return "Your allocation was withdrawn and the room has been released."

    else:
        # Was Pending or Waiting - just cancel, no room to free
        cursor.execute(
            "UPDATE applications SET status = 'Cancelled', reasoning = ? WHERE id = ?",
            ("You withdrew your application while on the waiting list.", app["id"])
        )
        conn.commit()
        conn.close()
        return "Your application has been withdrawn."