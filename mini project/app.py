# from flask import Flask, render_template, request, jsonify, redirect, session
# from werkzeug.security import generate_password_hash, check_password_hash
# import sqlite3
# import os
# from datetime import datetime

# app = Flask(__name__)
# app.secret_key = "SUPER_SECRET_KEY"   # CHANGE THIS BEFORE DEPLOYMENT

# # Create uploads folder
# os.makedirs("static/uploads", exist_ok=True)


# def connect_db():
#     return sqlite3.connect("database.db", check_same_thread=False)


# # --------------------------------------------------------
# # HOME PAGE
# # --------------------------------------------------------
# @app.route("/")
# def home():
#     if "user_id" not in session:
#         return redirect("/login")
#     return render_template("index.html")


# # --------------------------------------------------------
# # SIGNUP (SECURE)
# # --------------------------------------------------------
# @app.route("/signup", methods=["GET", "POST"])
# def signup():
#     if request.method == "POST":
#         username = request.form["username"]
#         email = request.form["email"]
#         password = request.form["password"]

#         password_hash = generate_password_hash(password)

#         db = connect_db()
#         cursor = db.cursor()

#         try:
#             cursor.execute("""
#                 INSERT INTO users (username, email, password_hash)
#                 VALUES (?, ?, ?)
#             """, (username, email, password_hash))

#             db.commit()
#             return redirect("/login")

#         except Exception as e:
#             return f"Error: Username or email already exists.<br>{e}"

#         finally:
#             db.close()

#     return render_template("signup.html")


# # --------------------------------------------------------
# # LOGIN (SECURE)
# # --------------------------------------------------------
# @app.route("/login", methods=["GET", "POST"])
# def login():
#     if request.method == "POST":
#         username = request.form["username"]
#         password = request.form["password"]

#         db = connect_db()
#         cursor = db.cursor()

#         cursor.execute("SELECT id, password_hash FROM users WHERE username=?", (username,))
#         user = cursor.fetchone()

#         db.close()

#         if user and check_password_hash(user[1], password):
#             session["user_id"] = user[0]
#             session["username"] = username
#             return redirect("/")
#         else:
#             return "❌ Invalid username or password"

#     return render_template("login.html")


# # --------------------------------------------------------
# # LOGOUT
# # --------------------------------------------------------
# @app.route("/logout")
# def logout():
#     session.clear()
#     return redirect("/login")


# # --------------------------------------------------------
# # FILE UPLOAD (per user)
# # --------------------------------------------------------
# @app.route("/upload", methods=["POST"])
# def upload():
#     if "user_id" not in session:
#         return jsonify({"error": "Not logged in"}), 401

#     try:
#         file = request.files["file"]
#         filename = file.filename

#         # Store files with user prefix to avoid conflicts
#         stored_name = f"user{session['user_id']}_{filename}"

#         path = os.path.join("static/uploads", stored_name)
#         file.save(path)

#         db = connect_db()
#         cursor = db.cursor()

#         cursor.execute("""
#             INSERT INTO uploads (user_id, filename, upload_time)
#             VALUES (?, ?, ?)
#         """, (session["user_id"], stored_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

#         db.commit()

#         return jsonify({"filename": stored_name, "message": "Upload successful!"})

#     except Exception as e:
#         return jsonify({"error": str(e)})

#     finally:
#         db.close()


# # --------------------------------------------------------
# # GET USER UPLOAD HISTORY (only for logged-in user)
# # --------------------------------------------------------
# @app.route("/files")
# def files():
#     if "user_id" not in session:
#         return jsonify({"error": "Not logged in"}), 401

#     db = connect_db()
#     cursor = db.cursor()

#     cursor.execute("""
#         SELECT filename, upload_time 
#         FROM uploads 
#         WHERE user_id=? ORDER BY upload_time DESC
#     """, (session["user_id"],))

#     records = cursor.fetchall()
#     db.close()

#     return jsonify(records)


# # --------------------------------------------------------
# # RUN FLASK
# # --------------------------------------------------------
# if __name__ == "__main__":
#     app.run(debug=True)



import os
import sqlite3
from datetime import datetime
import pandas as pd
from flask import Flask, render_template, request, redirect, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "SUPER_SECRET_KEY"

UPLOAD_FOLDER = "static/uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# -----------------------------
#  DATABASE
# -----------------------------
def connect_db():
    db = sqlite3.connect("database.db")
    db.row_factory = sqlite3.Row
    return db

def create_tables():
    db = connect_db()
    cursor = db.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            email TEXT,
            password_hash TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            filename TEXT,
            upload_time TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    db.commit()
    db.close()

create_tables()


# -----------------------------
#   AUTH ROUTES
# -----------------------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        db = connect_db()
        cursor = db.cursor()

        cursor.execute("SELECT * FROM users WHERE username=?", (username,))
        if cursor.fetchone():
            return "Username already exists!"

        hashed = generate_password_hash(password)

        cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?,?,?)",
            (username, email, hashed)
        )

        db.commit()
        db.close()

        return redirect("/login")

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = connect_db()
        cursor = db.cursor()

        cursor.execute("SELECT * FROM users WHERE username=?", (username,))
        user = cursor.fetchone()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect("/")
        else:
            return "Invalid credentials"

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# -----------------------------
#   HOME PAGE (Dashboard UI)
# -----------------------------
@app.route("/")
def home():
    return render_template("index.html")


# -----------------------------
#   FILE UPLOAD
# -----------------------------
@app.route("/upload", methods=["POST"])
def upload():
    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    filename = datetime.now().strftime("%Y%m%d%H%M%S_") + file.filename
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    db = connect_db()
    cursor = db.cursor()

    cursor.execute(
        "INSERT INTO uploads (user_id, filename, upload_time) VALUES (?,?,?)",
        (session["user_id"], filename, datetime.now())
    )

    db.commit()
    db.close()

    return jsonify({"message": "Success", "filename": filename})



# -----------------------------
#   FETCH USER UPLOADS
# -----------------------------
@app.route("/files")
def files():
    if "user_id" not in session:
        return jsonify([])

    db = connect_db()
    cursor = db.cursor()

    cursor.execute("SELECT filename, upload_time FROM uploads WHERE user_id=? ORDER BY id DESC",
                   (session["user_id"],))

    rows = cursor.fetchall()
    db.close()

    return jsonify([dict(r) for r in rows])


# -----------------------------
#   AGGREGATED DATA FOR DASHBOARD
# -----------------------------
@app.route("/data")
def data():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    db = connect_db()
    cursor = db.cursor()

    cursor.execute(
        "SELECT filename FROM uploads WHERE user_id=? ORDER BY id DESC LIMIT 1",
        (session["user_id"],)
    )

    row = cursor.fetchone()
    if not row:
        return jsonify({"error": "No uploads"}), 400

    filepath = f"static/uploads/{row['filename']}"

    # read file
    if filepath.endswith(".csv"):
        df = pd.read_csv(filepath)
    else:
        df = pd.read_excel(filepath)

    df.columns = df.columns.str.lower().str.strip()

    required = ["sales", "channel", "product", "date"]
    for col in required:
        if col not in df.columns:
            return jsonify({"error": f"Missing column: {col}"}), 400

    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.strftime("%b-%Y")

    total_sales = float(df["sales"].sum())

    sales_by_channel = (
        df.groupby("channel")["sales"].sum().reset_index().to_dict(orient="records")
    )

    sales_by_product = (
        df.groupby("product")["sales"].sum().reset_index().to_dict(orient="records")
    )

    sales_over_time = (
        df.groupby(["month", "channel"])["sales"].sum().reset_index().to_dict(orient="records")
    )

    return jsonify({
        "total_sales": total_sales,
        "sales_by_channel": sales_by_channel,
        "sales_by_product": sales_by_product,
        "sales_over_time": sales_over_time
    })


# -----------------------------
#   ADMIN PANEL (DEVELOPER ONLY)
# -----------------------------
@app.route("/admin")
def admin():
    # DEV PASSWORD PROTECTION
    dev_pass = "anshuu_admin"

    if request.args.get("key") != dev_pass:
        return "Unauthorized"

    db = connect_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()

    cursor.execute("""
        SELECT uploads.id, users.username, uploads.filename, uploads.upload_time
        FROM uploads
        JOIN users ON uploads.user_id = users.id
        ORDER BY uploads.id DESC
    """)
    uploads = cursor.fetchall()

    db.close()

    return jsonify({
        "users": [dict(u) for u in users],
        "uploads": [dict(u) for u in uploads]
    })


# Route to serve admin dashboard
@app.route("/admin-panel")
def admin_dashboard():
    return render_template("admin.html")

# -----------------------------


# Route to fetch users data
@app.route("/admin/users-data")
def admin_users_data():
    db = connect_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT 
            users.id, 
            users.username,
            COUNT(uploads.id) AS uploads
        FROM users
        LEFT JOIN uploads ON uploads.user_id = users.id
        GROUP BY users.id
    """)

    result = cursor.fetchall()
    db.close()

    users_list = [
        {"id": row[0], "username": row[1], "uploads": row[2]}
        for row in result
    ]

    return jsonify(users_list)
# -----------------------------

# Route to fetch uploads data
@app.route("/admin/uploads-data")
def admin_uploads_data():
    db = connect_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT id, user_id, filename, upload_time 
        FROM uploads
        ORDER BY upload_time DESC
    """)

    result = cursor.fetchall()
    db.close()

    uploads_list = [
        {"id": row[0], "user_id": row[1], "filename": row[2], "upload_time": row[3]}
        for row in result
    ]

    return jsonify(uploads_list)
# -----------------------------




if __name__ == "__main__":
    app.run(debug=True)
