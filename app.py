from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)

# =========================
# パス設定
# =========================
if not os.path.exists(app.instance_path):
    os.makedirs(app.instance_path)

DB_NAME = os.path.join(app.instance_path, "cafe_management.db")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

print("DBパス:", DB_NAME)

# =========================
# SECRET_KEY
# =========================
app.secret_key = os.environ.get("SECRET_KEY", "dev-key")

# =========================
# DB初期化
# =========================
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        with open(os.path.join(BASE_DIR, 'database/schema.sql')) as f:
            conn.executescript(f.read())

# 🔥 ここが超重要（Render対応）
init_db()

# =========================
# DB接続
# =========================
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# =========================
# ログイン必須デコレータ
# =========================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

# =========================
# アクセスログ
# =========================
def log_access():
    if "user_id" not in session:
        return

    if request.path.startswith("/static"):
        return
    
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO access_logs (user_id, path, method) VALUES (?, ?, ?)",
        (session["user_id"], request.path, request.method)
    )
    conn.commit()
    conn.close()

# =========================
# 商品登録
# =========================
@app.route("/products/new")
@login_required
def new_product():
    return render_template("product_form.html")

@app.route("/products", methods=["POST"])
@login_required
def create_product():
    name = request.form["name"]
    category = request.form["category"]
    price = request.form["price"]
    threshold = request.form["threshold"]
    quantity = request.form["quantity"]

    conn = get_db_connection()

    cursor = conn.execute(
        "INSERT INTO products (name, category, price, threshold) VALUES (?, ?, ?, ?)",
        (name, category, price, threshold)
    )
    product_id = cursor.lastrowid

    conn.execute(
        "INSERT INTO inventory (product_id, quantity, updated_at) VALUES (?, ?, ?)",
        (product_id, quantity, datetime.now())
    )

    conn.commit()
    conn.close()

    return redirect(url_for("product_list"))

# =========================
# 商品一覧
# =========================
@app.route("/")
@login_required
def product_list():
    conn = get_db_connection()

    products = conn.execute("""
        SELECT p.*, i.quantity, i.updated_at
        FROM products p
        LEFT JOIN inventory i ON p.id = i.product_id
    """).fetchall()

    last_updated = conn.execute("""
        SELECT MAX(updated_at) as last_updated
        FROM inventory
    """).fetchone()["last_updated"]

    conn.close()

    return render_template(
        "product_list.html",
        products=products,
        last_updated=last_updated
    )

# =========================
# 削除
# =========================
@app.route("/products/<int:id>/delete", methods=["POST"])
@login_required
def delete_product(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM products WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("product_list"))

# =========================
# ユーザ登録
# =========================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        if len(password) < 6:
            return "パスワードは6文字以上にしてください"

        password_hash = generate_password_hash(password)

        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                (name, email, password_hash)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            return "このメールはすでに使われています"
        finally:
            conn.close()

        return redirect(url_for("login"))

    return render_template("register.html")

# =========================
# ログイン
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]

            flash("ようこそ！" + user["name"] + "さん")
            return redirect(url_for("product_list"))
        else:
            error = "メールアドレスまたはパスワードが間違っています"

    return render_template("login.html", error=error)

# =========================
# ログアウト
# =========================
@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("ログアウトしました")
    return redirect(url_for("login"))

# =========================
# リクエスト前処理
# =========================
@app.before_request
def before_request():
    log_access()

# =========================
# 起動
# =========================
if __name__ == "__main__":
    app.run(debug=True)