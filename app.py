from flask import Flask, render_template, request, redirect, url_for, session
from database import init_db, create_user, verify_user

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
    return render_template("coming_soon.html", feature=feature)


@app.route("/admin-dashboard")
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    return render_template("dashboard_admin.html", user_id=session["user_id"])

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)