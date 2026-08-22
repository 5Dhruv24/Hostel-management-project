from flask import Flask, render_template, request, redirect, url_for, session
from database import (
    init_db, create_user, verify_user,
    seed_sample_data, get_all_applications, get_application_for_user, run_allocation,
    get_room_counts, get_waiting_list, get_waiting_position_for_user, withdraw_application,
    get_fairness_stats
)

app = Flask(__name__)
app.secret_key = "change-this-later-to-something-random"  # needed for login sessions

# --- Hardcoded admin credentials ---
# Only someone who knows these exact values can access the admin dashboard.
# Change these before your final demo/deployment.
ADMIN_ID = "admin"
ADMIN_PASSWORD = "admin123"

# --- Hostel application form link ---
HOSTEL_APPLICATION_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSfgCniUUBL1C7d9czhKm1qR3dFaN5WqQQxNlfrC8A9_8Dc6tQ/viewform?usp=publish-editor"

# Make sure the database + users table exist when the app starts
init_db()
seed_sample_data()


@app.route("/")
def home():
    # If someone visits the homepage, just send them to the login page
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user_id = request.form["user_id"]
        password = request.form["password"]

        if verify_user(user_id, password, "student"):
            session["user_id"] = user_id
            session["role"] = "student"
            return redirect(url_for("student_dashboard"))
        else:
            return render_template("login.html", error="Invalid ID or password.")

    return render_template("login.html")


@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        user_id = request.form["user_id"]
        password = request.form["password"]

        # Checked directly against the hardcoded values above, not the database
        if user_id == ADMIN_ID and password == ADMIN_PASSWORD:
            session["user_id"] = user_id
            session["role"] = "admin"
            return redirect(url_for("admin_dashboard"))
        else:
            return render_template("admin_login.html", error="Invalid admin credentials.")

    return render_template("admin_login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        user_id = request.form["user_id"]
        password = request.form["password"]

        # Public signup only ever creates student accounts
        success = create_user(user_id, password, "student")

        if success:
            return redirect(url_for("login"))
        else:
            return render_template("signup.html", error="This ID is already taken.")

    return render_template("signup.html")


@app.route("/logout")
def logout():
    session.clear()  # wipes user_id and role from the session
    return redirect(url_for("login"))


@app.route("/student-dashboard")
def student_dashboard():
    # Route protection: only logged-in students can see this page
    if session.get("role") != "student":
        return redirect(url_for("login"))

    return render_template("dashboard_student.html", user_id=session["user_id"])


@app.route("/apply")
def apply_hostel():
    if session.get("role") != "student":
        return redirect(url_for("login"))

    return render_template(
        "student_application.html",
        user_id=session["user_id"],
        form_url=HOSTEL_APPLICATION_FORM_URL
    )


# --- Placeholder page for features we haven't built yet ---

@app.route("/coming-soon/<feature>")
def coming_soon(feature):
    if "role" not in session:
        return redirect(url_for("login"))

    if session["role"] == "admin":
        back_url = url_for("admin_dashboard")
    else:
        back_url = url_for("student_dashboard")

    return render_template("coming_soon.html", feature=feature, back_url=back_url)


@app.route("/admin/student-list")
def student_list():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    applications = get_all_applications()
    return render_template("admin_student_list.html", applications=applications, user_id=session["user_id"])


@app.route("/admin/run-allocation", methods=["POST"])
def run_allocation_route():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    run_allocation()
    return redirect(url_for("student_list"))


@app.route("/my-allocation")
def my_allocation():
    if session.get("role") != "student":
        return redirect(url_for("login"))

    application = get_application_for_user(session["user_id"])

    waiting_position = None
    waiting_total = None
    if application and application["status"] == "Waiting":
        result = get_waiting_position_for_user(session["user_id"])
        if result:
            waiting_position, waiting_total = result

    return render_template(
        "my_allocation.html",
        application=application,
        user_id=session["user_id"],
        waiting_position=waiting_position,
        waiting_total=waiting_total
    )


@app.route("/withdraw-application", methods=["POST"])
def withdraw_application_route():
    if session.get("role") != "student":
        return redirect(url_for("login"))

    withdraw_application(session["user_id"])
    return redirect(url_for("my_allocation"))


@app.route("/waiting-list-status")
def waiting_list_status():
    if session.get("role") != "student":
        return redirect(url_for("login"))

    waiting_list = get_waiting_list()
    room_counts = get_room_counts()

    # Anonymize: show "First L." instead of full name/ID, to protect other
    # students' privacy while still keeping the list useful/transparent.
    display_list = []
    for row in waiting_list:
        name_parts = row["full_name"].split()
        first = name_parts[0]
        last_initial = f"{name_parts[1][0]}." if len(name_parts) > 1 else ""
        display_list.append({
            "position": row["position"],
            "display_name": f"{first} {last_initial}".strip(),
            "room_type": row["room_type"],
            "priority_note": row["priority_note"],
            "is_you": row["user_id"] == session["user_id"],
        })

    return render_template(
        "waiting_list_status.html",
        waiting_list=display_list,
        room_counts=room_counts,
        user_id=session["user_id"]
    )


@app.route("/admin/waiting-list")
def admin_waiting_list():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    waiting_list = get_waiting_list()
    room_counts = get_room_counts()
    all_applications = get_all_applications()

    counts = {
        "total_applications": len(all_applications),
        "allocated": len([a for a in all_applications if a["status"] == "Allocated"]),
        "waiting": len(waiting_list),
        "cancelled": len([a for a in all_applications if a["status"] == "Cancelled"]),
        "rooms_total": room_counts["total"],
        "rooms_occupied": room_counts["occupied"],
        "rooms_available": room_counts["available"],
    }

    return render_template(
        "admin_waiting_list.html",
        waiting_list=waiting_list,
        counts=counts,
        user_id=session["user_id"]
    )


@app.route("/fairness")
def student_fairness():
    if session.get("role") != "student":
        return redirect(url_for("login"))

    stats = get_fairness_stats()
    return render_template("student_fairness.html", stats=stats, user_id=session["user_id"])


@app.route("/admin/fairness")
def admin_fairness():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    stats = get_fairness_stats()
    return render_template("admin_fairness.html", stats=stats, user_id=session["user_id"])


@app.route("/admin-dashboard")
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    return render_template("dashboard_admin.html", user_id=session["user_id"])


if __name__ == "__main__":
    app.run(debug=True)