import os
import time

import psycopg2
import redis
from flask import Flask, jsonify, request
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

cache = redis.Redis(
    host=os.environ.get("REDIS_HOST", "redis"), port=6379, decode_responses=True
)
CART_TTL_SECONDS = 60 * 60 * 24  # carts expire after 24h


class StockError(Exception):
    pass


def get_conn(retries=10, delay=2):
    last_err = None
    for _ in range(retries):
        try:
            return psycopg2.connect(
                host=os.environ.get("DB_HOST", "db"),
                port=5432,
                dbname=os.environ["POSTGRES_DB"],
                user=os.environ["POSTGRES_USER"],
                password=os.environ["POSTGRES_PASSWORD"],
            )
        except psycopg2.OperationalError as err:
            last_err = err
            time.sleep(delay)
    raise last_err


def cart_key(sid):
    return f"cart:{sid}"


# ---------- health ----------
@app.get("/api/health")
def health():
    status = {"database": "down", "redis": "down"}
    try:
        get_conn(retries=1).close()
        status["database"] = "up"
    except Exception:  # noqa: BLE001
        pass
    try:
        cache.ping()
        status["redis"] = "up"
    except Exception:  # noqa: BLE001
        pass
    ok = all(v == "up" for v in status.values())
    return jsonify(status="ok" if ok else "degraded", **status), (200 if ok else 503)


# ---------- products ----------
@app.get("/api/products")
def products():
    conn = get_conn()
    try:
        with conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, name, description, price_cents, stock, emoji "
                "FROM products ORDER BY id"
            )
            return jsonify(cur.fetchall())
    finally:
        conn.close()


# ---------- cart (stored in Redis) ----------
def build_cart(sid):
    items = cache.hgetall(cart_key(sid))
    if not items:
        return {"items": [], "total_cents": 0}
    ids = [int(i) for i in items]
    conn = get_conn()
    try:
        with conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, name, price_cents, emoji FROM products WHERE id = ANY(%s)",
                (ids,),
            )
            found = {p["id"]: p for p in cur.fetchall()}
    finally:
        conn.close()
    lines, total = [], 0
    for pid, qty in items.items():
        p = found.get(int(pid))
        if not p:
            continue
        qty = int(qty)
        lines.append({**p, "quantity": qty, "line_cents": p["price_cents"] * qty})
        total += p["price_cents"] * qty
    return {"items": lines, "total_cents": total}


@app.get("/api/cart/<sid>")
def get_cart(sid):
    return jsonify(build_cart(sid))


@app.post("/api/cart/<sid>")
def add_to_cart(sid):
    data = request.get_json(silent=True) or {}
    try:
        pid = int(data["product_id"])
        qty = int(data.get("quantity", 1))
    except (KeyError, ValueError, TypeError):
        return jsonify(error="product_id and quantity must be numbers"), 400

    conn = get_conn()
    try:
        with conn, conn.cursor() as cur:
            cur.execute("SELECT 1 FROM products WHERE id = %s", (pid,))
            if not cur.fetchone():
                return jsonify(error="product not found"), 404
    finally:
        conn.close()

    new_qty = cache.hincrby(cart_key(sid), str(pid), qty)
    if new_qty <= 0:
        cache.hdel(cart_key(sid), str(pid))
    cache.expire(cart_key(sid), CART_TTL_SECONDS)
    return jsonify(build_cart(sid))


@app.delete("/api/cart/<sid>")
def clear_cart(sid):
    cache.delete(cart_key(sid))
    return jsonify(items=[], total_cents=0)


# ---------- checkout (writes to PostgreSQL) ----------
@app.post("/api/checkout")
def checkout():
    data = request.get_json(silent=True) or {}
    sid = (data.get("sid") or "").strip()
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    if not (sid and name and email):
        return jsonify(error="sid, name and email are required"), 400

    items = cache.hgetall(cart_key(sid))
    if not items:
        return jsonify(error="cart is empty"), 400

    conn = get_conn()
    try:
        with conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            ids = [int(i) for i in items]
            cur.execute(
                "SELECT id, name, price_cents, stock FROM products "
                "WHERE id = ANY(%s) FOR UPDATE",
                (ids,),
            )
            found = {p["id"]: p for p in cur.fetchall()}

            total = 0
            for pid, qty in items.items():
                p, qty = found.get(int(pid)), int(qty)
                if not p:
                    raise StockError(f"product {pid} no longer exists")
                if p["stock"] < qty:
                    raise StockError(f"not enough stock for {p['name']}")
                total += p["price_cents"] * qty

            cur.execute(
                "INSERT INTO orders (customer_name, customer_email, total_cents) "
                "VALUES (%s, %s, %s) RETURNING id",
                (name, email, total),
            )
            order_id = cur.fetchone()["id"]

            for pid, qty in items.items():
                p, qty = found[int(pid)], int(qty)
                cur.execute(
                    "INSERT INTO order_items (order_id, product_id, quantity, price_cents) "
                    "VALUES (%s, %s, %s, %s)",
                    (order_id, p["id"], qty, p["price_cents"]),
                )
                cur.execute(
                    "UPDATE products SET stock = stock - %s WHERE id = %s",
                    (qty, p["id"]),
                )
    except StockError as err:
        return jsonify(error=str(err)), 409
    finally:
        conn.close()

    cache.delete(cart_key(sid))
    return jsonify(order_id=order_id, total_cents=total), 201


@app.get("/api/orders")
def orders():
    conn = get_conn()
    try:
        with conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, customer_name, total_cents, created_at "
                "FROM orders ORDER BY id DESC LIMIT 10"
            )
            rows = cur.fetchall()
            for r in rows:
                r["created_at"] = r["created_at"].isoformat()
            return jsonify(rows)
    finally:
        conn.close()
