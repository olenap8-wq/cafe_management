from flask import Flask, render_template, request, redirect, url_for
import sqlite3

def init_db():
    with sqlite3.connect('cafe_management.db') as conn:
        with open('database/schema.sql') as f:
            conn.executescript(f.read())

from datetime import datetime

import os  # ← 追加

app = Flask(__name__)

# ↓ ここを書き換える
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "cafe_management.db")


def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# 商品一覧
@app.route("/")
def product_list():
    conn = get_db_connection()
    products = conn.execute("""
        SELECT p.*, i.quantity
        FROM products p
        LEFT JOIN inventory i ON p.id = i.product_id
    """).fetchall()
    conn.close()
    return render_template("product_list.html", products=products)


# 商品登録ページ
@app.route("/products/new")
def new_product():
    return render_template("product_form.html")


# 商品登録処理
@app.route("/products", methods=["POST"])
def create_product():
    name = request.form["name"]
    category = request.form["category"]
    threshold = request.form["threshold"]
    quantity = request.form["quantity"]

    conn = get_db_connection()

    # productsに登録
    cursor = conn.execute(
        "INSERT INTO products (name, category, threshold) VALUES (?, ?, ?)",
        (name, category, threshold)
    )
    product_id = cursor.lastrowid

    # inventoryに登録（初期在庫）
    conn.execute(
        "INSERT INTO inventory (product_id, quantity, updated_at) VALUES (?, ?, ?)",
        (product_id, quantity, datetime.now())
    )

    conn.commit()
    conn.close()

    return redirect(url_for("product_list"))


import os

if __name__ == "__main__":
    if not os.path.exists("cafe_management.db"):
        init_db()
    app.run(debug=True)