from flask import Flask, render_template, request, redirect, url_for, session
from database import init_db, create_user, verify_user

app = Flask(__name__)
app.secret_key = "change-this-later-to-something-random"  # needed for login sessions

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
        role = request.form["role"]  # "student" or "admin"

        if verify_user(user_id, password, role):
            session["user_id"] = user_id
            session["role"] = role

            if role == "student":
                return redirect(url_for("student_dashboard"))
            else:
                return redirect(url_for("admin_dashboard"))
        else:
            return render_template("login.html", error="Invalid ID, password, or role.")

    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        user_id = request.form["user_id"]
        password = request.form["password"]
        role = request.form["role"]

        success = create_user(user_id, password, role)

        if success:
            return redirect(url_for("login"))
        else:
            return render_template("signup.html", error="This ID is already taken.")

    return render_template("signup.html")


# --- Placeholder pages, we'll build these properly later ---

@app.route("/student-dashboard")
def student_dashboard():
    return "<h1>Student Dashboard (coming soon)</h1>"


@app.route("/admin-dashboard")
def admin_dashboard():
    return "<h1>Admin Dashboard (coming soon)</h1>"


if __name__ == "__main__":
    app.run(debug=True)