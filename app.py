from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)

# パス設定
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "cafe_management.db")


# =========================
# DB初期化
# =========================
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        with open(os.path.join(BASE_DIR, 'database/schema.sql')) as f:
            conn.executescript(f.read())


# =========================
# DB接続
# =========================
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# =========================
# 新規作成（Create）
# =========================
@app.route("/products/new")
def new_product():
    return render_template("product_form.html")


@app.route("/products", methods=["POST"])
def create_product():
    name = request.form["name"]
    category = request.form["category"]
    price = request.form["price"]          # ← 追加
    threshold = request.form["threshold"]
    quantity = request.form["quantity"]

    conn = get_db_connection()

    # productsテーブルに登録（unit追加）
    cursor = conn.execute(
        "INSERT INTO products (name, category, price, threshold) VALUES (?, ?, ?, ?)",
        (name, category, price, threshold)
    )
    product_id = cursor.lastrowid

    # inventoryテーブルに登録
    conn.execute(
        "INSERT INTO inventory (product_id, quantity, updated_at) VALUES (?, ?, ?)",
        (product_id, quantity, datetime.now())
    )

    conn.commit()
    conn.close()

    return redirect(url_for("product_list"))


# =========================
# 編集（Update）
# =========================

# 編集ページ
@app.route("/products/<int:id>/edit")
def edit_product(id):
    conn = get_db_connection()
    product = conn.execute(
        "SELECT * FROM products WHERE id = ?", (id,)
    ).fetchone()
    conn.close()
    return render_template("product_form.html", product=product)


# 更新処理
@app.route("/")
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
# 削除（Delete）
# =========================
@app.route("/products/<int:id>/delete", methods=["POST"])
def delete_product(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM products WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("product_list"))


# =========================
# 起動
# =========================
if __name__ == "__main__":
    if not os.path.exists(DB_NAME):
        init_db()
    app.run(debug=True)