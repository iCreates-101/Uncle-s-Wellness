"""Supabase (Postgres via REST) database layer with SQLite fallback for demo mode.

The public API matches the original Firebase-backed layer (firebase_db.py) so
the rest of the app is unaffected. When SUPABASE_URL and a Supabase key are
configured the app talks to Supabase via its REST API; otherwise it falls back
to the local SQLite file.
"""

import os
import sys
import sqlite3
import datetime
import json
import uuid

# ─── Supabase (lazy) ───────────────────────────────
_supabase_client = None

# Columns returned by PostgREST as strings (numeric/decimal types) that the
# app expects to use as numbers.
_NUMERIC_COLS = {
    "products": {"price", "cost_price", "stock"},
    "carts": {"quantity"},
    "orders": {"subtotal", "tax", "total", "shipping", "discount"},
    "order_items": {"price", "quantity", "total"},
}


def _coerce_row(row, table):
    """Convert PostgREST numeric strings back into int/float."""
    num_cols = _NUMERIC_COLS.get(table, set())
    for k in num_cols:
        v = row.get(k)
        if isinstance(v, str) and v:
            try:
                row[k] = int(v) if v.lstrip("-").isdigit() else float(v)
            except ValueError:
                pass
    return row


def _init_supabase():
    global _supabase_client
    try:
        from supabase import create_client
    except ImportError:
        return None

    url = os.environ.get("SUPABASE_URL")
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_ANON_KEY")
        or os.environ.get("SUPABASE_KEY")
    )
    if not url or not key:
        return None

    try:
        _supabase_client = create_client(url, key)
        # Light connectivity/schema check (throws if unreachable)
        _supabase_client.table("users").select("id").limit(1).execute()
        return _supabase_client
    except Exception:
        _supabase_client = None
        return None


# ─── SQLite fallback ─────────────────────────────────
_sqlite_conn = None
USE_SQLITE = False

DB_PATH = os.path.join(os.path.dirname(__file__), "uncles_wellness.db")


def _init_sqlite():
    global _sqlite_conn, USE_SQLITE
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY, name TEXT, email TEXT UNIQUE,
            password TEXT, role TEXT DEFAULT 'customer',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS categories (
            id TEXT PRIMARY KEY, name TEXT, slug TEXT, description TEXT,
            subcategories TEXT DEFAULT '[]'
        );
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY, name TEXT, slug TEXT, description TEXT,
            price REAL DEFAULT 0, cost_price REAL DEFAULT 0,
            stock INTEGER DEFAULT 0, category_id TEXT,
            subcategory TEXT DEFAULT '', subcategory_slug TEXT DEFAULT '',
            featured INTEGER DEFAULT 0, active INTEGER DEFAULT 1,
            barcode TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS carts (
            id TEXT PRIMARY KEY, session_id TEXT, product_id TEXT,
            quantity INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY, order_number TEXT, user_id TEXT,
            customer_name TEXT, customer_email TEXT, customer_phone TEXT,
            shipping_address TEXT, payment_method TEXT DEFAULT 'cod',
            subtotal REAL DEFAULT 0, tax REAL DEFAULT 0, total REAL DEFAULT 0,
            shipping REAL DEFAULT 0,
            order_status TEXT DEFAULT 'pending',
            payment_status TEXT DEFAULT 'pending',
            notes TEXT, pos_order INTEGER DEFAULT 0,
            discount REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS order_items (
            id TEXT PRIMARY KEY, order_id TEXT, product_id TEXT,
            product_name TEXT, price REAL DEFAULT 0,
            quantity INTEGER DEFAULT 0, total REAL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS logs (
            id TEXT PRIMARY KEY, action TEXT, description TEXT,
            user_id TEXT, user_name TEXT, target_type TEXT, target_id TEXT,
            metadata TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    # Migrate existing tables if needed
    for col in ["subcategories"]:
        try:
            conn.execute(f"ALTER TABLE categories ADD COLUMN {col} TEXT DEFAULT '[]'")
        except Exception:
            pass
    for col in ["subcategory", "subcategory_slug"]:
        try:
            conn.execute(f"ALTER TABLE products ADD COLUMN {col} TEXT DEFAULT ''")
        except Exception:
            pass
    for col in ["shipping"]:
        try:
            conn.execute(f"ALTER TABLE orders ADD COLUMN {col} REAL DEFAULT 0")
        except Exception:
            pass
    conn.commit()
    _sqlite_conn = conn
    USE_SQLITE = True
    return conn


# ─── Init ───────────────────────────────────────
_INIT_DONE = False


def init_db():
    global _INIT_DONE
    if _INIT_DONE:
        return _supabase_client or _sqlite_conn
    sb = _init_supabase()
    if sb is not None:
        _INIT_DONE = True
        return sb
    result = _init_sqlite()
    _INIT_DONE = True
    return result


def get_db():
    if not _INIT_DONE:
        init_db()
    if _supabase_client is not None:
        return _supabase_client
    if _sqlite_conn is not None:
        return _sqlite_conn
    return init_db()


# Auto-init on import so all functions work without explicit init_db() call.
init_db()


# ─── Helpers ────────────────────────────────────
def _new_id():
    return uuid.uuid4().hex[:20]


def _now():
    return datetime.datetime.utcnow()


def _iso(value):
    if isinstance(value, datetime.datetime):
        return value.isoformat()
    if isinstance(value, datetime.date):
        return datetime.datetime(value.year, value.month, value.day).isoformat()
    return str(value)


class Doc:
    """Wraps a Supabase row or SQLite row for uniform attribute access."""
    __slots__ = ("_data",)

    def __init__(self, data, doc_id=None):
        if isinstance(data, dict):
            d = dict(data)
            if doc_id is not None:
                d["id"] = doc_id
        else:
            d = dict(data) if data else {}
        object.__setattr__(self, "_data", d)

    def __getattr__(self, name):
        try:
            return self._data[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        self._data[name] = value

    def __repr__(self):
        return f"<Doc {self._data.get('name', self._data.get('id', '?'))}>"

    def to_dict(self):
        return dict(self._data)

    @property
    def id(self):
        return self._data.get("id")


# ─── Supabase helpers ───────────────────────────
def _srows(table, rows):
    return [Doc(_coerce_row(dict(r), table)) for r in rows or []]


def _get1(table, **filters):
    """Return the first matching row as a Doc, or None."""
    q = _supabase_client.table(table).select("*")
    for k, v in filters.items():
        q = q.eq(k, v)
    res = q.limit(1).execute()
    rows = _srows(table, res.data)
    return rows[0] if rows else None


def _insert(table, data):
    rec = dict(data)
    rid = rec.get("id") or _new_id()
    rec["id"] = rid
    if "created_at" not in rec:
        rec["created_at"] = _now().isoformat()
    _supabase_client.table(table).insert(rec).execute()
    return rid


def _update(table, doc_id, data):
    if not data:
        return
    _supabase_client.table(table).update(dict(data)).eq("id", doc_id).execute()


def _delete(table, doc_id):
    _supabase_client.table(table).delete().eq("id", doc_id).execute()


def _count(table, **filters):
    q = _supabase_client.table(table).select("*", count="exact")
    for k, v in filters.items():
        q = q.eq(k, v)
    res = q.execute()
    return res.count if res.count is not None else len(res.data or [])


# ─── SQLite helpers ─────────────────────────────
def _row_to_doc(row):
    if row is None:
        return None
    return Doc(dict(row))


def _rows_to_docs(rows):
    return [Doc(dict(r)) for r in rows]


def _fquery(table, where=None, order_by=None, limit_val=None):
    """Minimal SQL query builder for common SQLite patterns."""
    sql = f"SELECT * FROM {table}"
    params = []
    if where:
        clauses = []
        for k, v in where:
            clauses.append(f"{k} = ?")
            params.append(v)
        sql += " WHERE " + " AND ".join(clauses)
    if order_by:
        sql += f" ORDER BY {order_by[0]} {order_by[1]}"
    if limit_val:
        sql += f" LIMIT {limit_val}"
    cur = get_db().execute(sql, params)
    return _rows_to_docs(cur.fetchall())


def _fget(table, doc_id):
    cur = get_db().execute(f"SELECT * FROM {table} WHERE id = ?", (doc_id,))
    return _row_to_doc(cur.fetchone())


def _finsert(table, data):
    data["id"] = data.get("id", _new_id())
    cols = ", ".join(data.keys())
    placeholders = ", ".join("?" for _ in data)
    vals = list(data.values())
    get_db().execute(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})", vals)
    get_db().commit()
    return data["id"]


def _fupdate(table, doc_id, data):
    if not data:
        return
    sets = ", ".join(f"{k} = ?" for k in data)
    vals = list(data.values()) + [doc_id]
    get_db().execute(f"UPDATE {table} SET {sets} WHERE id = ?", vals)
    get_db().commit()


def _fdelete(table, doc_id):
    get_db().execute(f"DELETE FROM {table} WHERE id = ?", (doc_id,))
    get_db().commit()


# ═══════════════════════════════════════════════════════════════
#  USERS
# ═══════════════════════════════════════════════════════════════
def get_user_by_email(email):
    if not USE_SQLITE:
        return _get1("users", email=email)
    return _row_to_doc(get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone())


def get_user_by_id(uid):
    if not USE_SQLITE:
        return _get1("users", id=uid)
    return _fget("users", uid)


def create_user(data):
    if not USE_SQLITE:
        return _insert("users", data)
    data["created_at"] = data.get("created_at", _now().isoformat())
    return _finsert("users", data)


# ═══════════════════════════════════════════════════════════════
#  CATEGORIES
# ═══════════════════════════════════════════════════════════════
def get_all_categories():
    if not USE_SQLITE:
        res = _supabase_client.table("categories").select("*").order("name").execute()
        return _srows("categories", res.data)
    return _fquery("categories", order_by=("name", "ASC"))


def get_category_by_slug(slug):
    if not USE_SQLITE:
        return _get1("categories", slug=slug)
    return _row_to_doc(get_db().execute("SELECT * FROM categories WHERE slug = ?", (slug,)).fetchone())


def get_category_by_id(cid):
    if not USE_SQLITE:
        return _get1("categories", id=cid)
    return _fget("categories", cid)


def create_category(data):
    if not USE_SQLITE:
        rec = dict(data)
        rec["id"] = rec.get("id") or _new_id()
        _supabase_client.table("categories").insert(rec).execute()
        return rec["id"]
    return _finsert("categories", data)


def delete_category(cid):
    if not USE_SQLITE:
        _delete("categories", cid)
        return
    _fdelete("categories", cid)


# ═══════════════════════════════════════════════════════════════
#  PRODUCTS
# ═══════════════════════════════════════════════════════════════
def _attach_category(products):
    for p in products:
        cid = p._data.get("category_id")
        if cid:
            cat = get_category_by_id(cid)
            p._data["category"] = cat


def get_all_products(active_only=True, category=None, featured=None,
                     sort_by=None, sort_dir="desc", limit_val=None,
                     subcategory=None):
    if not USE_SQLITE:
        q = _supabase_client.table("products").select("*")
        if active_only:
            q = q.eq("active", 1)
        if category:
            q = q.eq("category_id", category)
        if featured is not None:
            q = q.eq("featured", (1 if featured else 0))
        if subcategory:
            q = q.eq("subcategory_slug", subcategory)
        q = q.order(sort_by or "created_at", desc=(sort_dir == "desc"))
        if limit_val:
            q = q.limit(limit_val)
        result = _srows("products", q.execute().data)
        _attach_category(result)
        return result

    sql = "SELECT * FROM products WHERE 1=1"
    params = []
    if active_only:
        sql += " AND active = 1"
    if category:
        sql += " AND category_id = ?"
        params.append(category)
    if featured is not None:
        sql += " AND featured = ?"
        params.append(1 if featured else 0)
    if subcategory:
        sql += " AND subcategory_slug = ?"
        params.append(subcategory)
    order_field = sort_by or "created_at"
    dir_str = "DESC" if sort_dir == "desc" else "ASC"
    sql += f" ORDER BY {order_field} {dir_str}"
    if limit_val:
        sql += f" LIMIT {limit_val}"
    result = _rows_to_docs(get_db().execute(sql, params).fetchall())
    _attach_category(result)
    return result


def search_products(query_text, active_only=True):
    if not USE_SQLITE:
        q = _supabase_client.table("products").select("*")
        if active_only:
            q = q.eq("active", 1)
        qt = query_text.lower()
        q = q.or_(f"name.ilike.%{qt}%,description.ilike.%{qt}%,barcode.ilike.%{qt}%")
        matched = _srows("products", q.execute().data)
        _attach_category(matched)
        return matched

    sql = "SELECT * FROM products WHERE 1=1"
    params = []
    if active_only:
        sql += " AND active = 1"
    sql += " AND (LOWER(name) LIKE ? OR LOWER(description) LIKE ? OR LOWER(barcode) LIKE ?)"
    like = f"%{query_text.lower()}%"
    params.extend([like, like, like])
    result = _rows_to_docs(get_db().execute(sql, params).fetchall())
    _attach_category(result)
    return result


def get_product_by_slug(slug):
    if not USE_SQLITE:
        p = _get1("products", slug=slug)
        if p:
            _attach_category([p])
        return p
    p = _row_to_doc(get_db().execute("SELECT * FROM products WHERE slug = ?", (slug,)).fetchone())
    if p:
        _attach_category([p])
    return p


def get_product_by_barcode(barcode):
    if not USE_SQLITE:
        return _get1("products", barcode=barcode)
    return _row_to_doc(get_db().execute("SELECT * FROM products WHERE barcode = ?", (barcode,)).fetchone())


def get_product_by_id(pid):
    if not USE_SQLITE:
        p = _get1("products", id=pid)
        if p:
            _attach_category([p])
        return p
    p = _fget("products", pid)
    if p:
        _attach_category([p])
    return p


def get_related_products(category_id, exclude_id, limit_val=4):
    if not USE_SQLITE:
        q = (_supabase_client.table("products").select("*")
             .eq("active", 1).eq("category_id", category_id)
             .neq("id", exclude_id).limit(limit_val))
        result = _srows("products", q.execute().data)
        _attach_category(result)
        return result

    rows = get_db().execute(
        "SELECT * FROM products WHERE active = 1 AND category_id = ? AND id != ? LIMIT ?",
        (category_id, exclude_id, limit_val)
    ).fetchall()
    result = _rows_to_docs(rows)
    _attach_category(result)
    return result


def create_product(data):
    if not USE_SQLITE:
        rec = dict(data)
        rec["id"] = rec.get("id") or _new_id()
        rec["created_at"] = rec.get("created_at", _now().isoformat())
        rec["active"] = rec.get("active", 1)
        rec["featured"] = rec.get("featured", 0)
        rec["stock"] = rec.get("stock", 0)
        _supabase_client.table("products").insert(rec).execute()
        return rec["id"]
    data["created_at"] = data.get("created_at", _now().isoformat())
    data["active"] = data.get("active", 1)
    data["featured"] = data.get("featured", 0)
    data["stock"] = data.get("stock", 0)
    return _finsert("products", data)


def update_product(pid, data):
    if not USE_SQLITE:
        _update("products", pid, data)
        return
    _fupdate("products", pid, data)


def delete_product(pid):
    if not USE_SQLITE:
        _delete("products", pid)
        return
    _fdelete("products", pid)


def count_products(active_only=True):
    if not USE_SQLITE:
        if active_only:
            return _count("products", active=1)
        return _count("products")
    sql = "SELECT COUNT(*) as cnt FROM products"
    params = []
    if active_only:
        sql += " WHERE active = 1"
    return get_db().execute(sql, params).fetchone()["cnt"]


def count_low_stock(threshold=10):
    if not USE_SQLITE:
        q = (_supabase_client.table("products").select("*", count="exact")
             .eq("active", 1).lt("stock", threshold))
        res = q.execute()
        return res.count if res.count is not None else len(res.data or [])
    return get_db().execute(
        "SELECT COUNT(*) as cnt FROM products WHERE active = 1 AND stock < ?", (threshold,)
    ).fetchone()["cnt"]


def get_inventory():
    if not USE_SQLITE:
        res = _supabase_client.table("products").select("*").order("stock").execute()
        result = _srows("products", res.data)
        _attach_category(result)
        return result
    result = _fquery("products", order_by=("stock", "ASC"))
    _attach_category(result)
    return result


# ═══════════════════════════════════════════════════════════════
#  CART
# ═══════════════════════════════════════════════════════════════
def get_cart_items(session_id, active_only=True):
    if not USE_SQLITE:
        q = _supabase_client.table("carts").select("*").eq("session_id", session_id)
        items = _srows("carts", q.execute().data)
        for item in items:
            prod = get_product_by_id(item.product_id)
            if prod:
                item._data["name"] = prod.name
                item._data["price"] = prod.price
                item._data["slug"] = prod.slug
                item._data["stock"] = prod.stock
                item._data["image"] = prod._data.get("image")
                item._data["product_active"] = prod.active
            else:
                item._data["product_active"] = 0
        if active_only:
            items = [i for i in items if i._data.get("product_active")]
        return items

    sql = """SELECT c.*, p.name, p.price, p.slug, p.stock,
                    p.active as product_active
             FROM carts c JOIN products p ON c.product_id = p.id
             WHERE c.session_id = ?"""
    rows = get_db().execute(sql, (session_id,)).fetchall()
    items = _rows_to_docs(rows)
    if active_only:
        items = [i for i in items if i._data.get("product_active")]
    return items


def get_cart_item_by_product(session_id, product_id):
    if not USE_SQLITE:
        q = (_supabase_client.table("carts").select("*")
             .eq("session_id", session_id).eq("product_id", product_id).limit(1))
        rows = _srows("carts", q.execute().data)
        return rows[0] if rows else None
    return _row_to_doc(get_db().execute(
        "SELECT * FROM carts WHERE session_id = ? AND product_id = ?", (session_id, product_id)
    ).fetchone())


def add_cart_item(session_id, product_id, quantity=1):
    if not USE_SQLITE:
        existing = get_cart_item_by_product(session_id, product_id)
        if existing:
            new_qty = (existing._data.get("quantity") or 0) + quantity
            _update("carts", existing.id, {"quantity": new_qty})
            return existing.id
        rec = {"session_id": session_id, "product_id": product_id, "quantity": quantity}
        return _insert("carts", rec)

    existing = get_cart_item_by_product(session_id, product_id)
    if existing:
        new_qty = (existing._data.get("quantity") or 0) + quantity
        _fupdate("carts", existing.id, {"quantity": new_qty})
        return existing.id
    return _finsert("carts", {"session_id": session_id, "product_id": product_id, "quantity": quantity})


def update_cart_quantity(cart_id, quantity):
    if not USE_SQLITE:
        if quantity <= 0:
            _delete("carts", cart_id)
        else:
            _update("carts", cart_id, {"quantity": quantity})
        return
    if quantity <= 0:
        _fdelete("carts", cart_id)
    else:
        _fupdate("carts", cart_id, {"quantity": quantity})


def remove_cart_item(cart_id):
    if not USE_SQLITE:
        _delete("carts", cart_id)
        return
    _fdelete("carts", cart_id)


def clear_cart(session_id):
    if not USE_SQLITE:
        _supabase_client.table("carts").delete().eq("session_id", session_id).execute()
        return
    get_db().execute("DELETE FROM carts WHERE session_id = ?", (session_id,))
    get_db().commit()


def get_cart_count(session_id):
    if not USE_SQLITE:
        res = _supabase_client.table("carts").select("quantity").eq("session_id", session_id).execute()
        return sum(float(r.get("quantity") or 0) for r in (res.data or []))
    row = get_db().execute("SELECT COALESCE(SUM(quantity),0) as cnt FROM carts WHERE session_id = ?", (session_id,)).fetchone()
    return row["cnt"]


# ═══════════════════════════════════════════════════════════════
#  ORDERS
# ═══════════════════════════════════════════════════════════════
def create_order(data):
    if not USE_SQLITE:
        rec = dict(data)
        rec["id"] = rec.get("id") or _new_id()
        rec["created_at"] = rec.get("created_at", _now().isoformat())
        rec["payment_status"] = rec.get("payment_status", "pending")
        rec["order_status"] = rec.get("order_status", "pending")
        rec["pos_order"] = rec.get("pos_order", 0)
        _supabase_client.table("orders").insert(rec).execute()
        return rec["id"]
    data["created_at"] = data.get("created_at", _now().isoformat())
    data["payment_status"] = data.get("payment_status", "pending")
    data["order_status"] = data.get("order_status", "pending")
    data["pos_order"] = data.get("pos_order", 0)
    return _finsert("orders", data)


def get_order_by_id(oid):
    if not USE_SQLITE:
        return _get1("orders", id=oid)
    return _fget("orders", oid)


def get_order_by_number(order_number):
    if not USE_SQLITE:
        return _get1("orders", order_number=order_number)
    return _row_to_doc(get_db().execute("SELECT * FROM orders WHERE order_number = ?", (order_number,)).fetchone())


def get_orders_by_user(user_id, limit_val=50):
    if not USE_SQLITE:
        q = (_supabase_client.table("orders").select("*")
             .eq("user_id", user_id).order("created_at", desc=True).limit(limit_val))
        return _srows("orders", q.execute().data)
    return _fquery("orders", where=[("user_id", user_id)], order_by=("created_at", "DESC"), limit_val=limit_val)


def get_all_orders(status=None, limit_val=100):
    if not USE_SQLITE:
        q = _supabase_client.table("orders").select("*")
        if status:
            q = q.eq("order_status", status)
        q = q.order("created_at", desc=True).limit(limit_val)
        return _srows("orders", q.execute().data)
    if status:
        return _fquery("orders", where=[("order_status", status)], order_by=("created_at", "DESC"), limit_val=limit_val)
    return _fquery("orders", order_by=("created_at", "DESC"), limit_val=limit_val)


def get_pos_orders(limit_val=50):
    if not USE_SQLITE:
        q = (_supabase_client.table("orders").select("*")
             .eq("pos_order", 1).order("created_at", desc=True).limit(limit_val))
        return _srows("orders", q.execute().data)
    return _fquery("orders", where=[("pos_order", 1)], order_by=("created_at", "DESC"), limit_val=limit_val)


def get_recent_orders(limit_val=5):
    if not USE_SQLITE:
        q = _supabase_client.table("orders").select("*").order("created_at", desc=True).limit(limit_val)
        return _srows("orders", q.execute().data)
    return _fquery("orders", order_by=("created_at", "DESC"), limit_val=limit_val)


def update_order(oid, data):
    if not USE_SQLITE:
        _update("orders", oid, data)
        return
    _fupdate("orders", oid, data)


def count_orders():
    if not USE_SQLITE:
        return _count("orders")
    return get_db().execute("SELECT COUNT(*) as cnt FROM orders").fetchone()["cnt"]


def total_revenue():
    if not USE_SQLITE:
        res = _supabase_client.table("orders").select("total").execute()
        return sum(float(r.get("total") or 0) for r in (res.data or []))
    row = get_db().execute("SELECT COALESCE(SUM(total),0) as rev FROM orders").fetchone()
    return row["rev"]


def count_users():
    if not USE_SQLITE:
        return _count("users")
    return get_db().execute("SELECT COUNT(*) as cnt FROM users").fetchone()["cnt"]


# ═══════════════════════════════════════════════════════════════
#  ORDER ITEMS
# ═══════════════════════════════════════════════════════════════
def get_order_items(order_id):
    if not USE_SQLITE:
        q = _supabase_client.table("order_items").select("*").eq("order_id", order_id)
        return _srows("order_items", q.execute().data)
    return _fquery("order_items", where=[("order_id", order_id)])


def create_order_item(data):
    if not USE_SQLITE:
        return _insert("order_items", data)
    return _finsert("order_items", data)


# ═══════════════════════════════════════════════════════════════
#  ACTIVITY LOGS
# ═══════════════════════════════════════════════════════════════
def create_log(action, description, user_id=None, user_name=None,
               target_type=None, target_id=None, metadata=None):
    if not USE_SQLITE:
        rec = {
            "action": action,
            "description": description,
            "user_id": user_id,
            "user_name": user_name,
            "target_type": target_type,
            "target_id": target_id,
            "metadata": metadata or {},
            "created_at": _now().isoformat(),
        }
        return _insert("logs", rec)
    data = {
        "action": action,
        "description": description,
        "user_id": user_id,
        "user_name": user_name,
        "target_type": target_type,
        "target_id": target_id,
        "metadata": json.dumps(metadata or {}),
        "created_at": _now().isoformat(),
    }
    return _finsert("logs", data)


def get_logs(limit_val=100):
    if not USE_SQLITE:
        q = _supabase_client.table("logs").select("*").order("created_at", desc=True).limit(limit_val)
        return _srows("logs", q.execute().data)
    return _fquery("logs", order_by=("created_at", "DESC"), limit_val=limit_val)


def get_logs_by_date_range(start_date, end_date, limit_val=500):
    if not USE_SQLITE:
        q = (_supabase_client.table("logs").select("*")
             .gte("created_at", _iso(start_date))
             .lte("created_at", _iso(end_date))
             .order("created_at", desc=True).limit(limit_val))
        return _srows("logs", q.execute().data)

    start_str = start_date.isoformat() if hasattr(start_date, "isoformat") else str(start_date)
    end_str = end_date.isoformat() if hasattr(end_date, "isoformat") else str(end_date)
    rows = get_db().execute(
        "SELECT * FROM logs WHERE created_at >= ? AND created_at <= ? ORDER BY created_at DESC LIMIT ?",
        (start_str, end_str, limit_val)
    ).fetchall()
    return _rows_to_docs(rows)


# ═══════════════════════════════════════════════════════════════
#  REPORTS
# ═══════════════════════════════════════════════════════════════
def get_orders_by_date_range(start_date, end_date):
    if not USE_SQLITE:
        q = (_supabase_client.table("orders").select("*")
             .gte("created_at", _iso(start_date))
             .lte("created_at", _iso(end_date))
             .order("created_at", desc=True))
        return _srows("orders", q.execute().data)

    start_str = start_date.isoformat() if hasattr(start_date, "isoformat") else str(start_date)
    end_str = end_date.isoformat() if hasattr(end_date, "isoformat") else str(end_date)
    return _rows_to_docs(get_db().execute(
        "SELECT * FROM orders WHERE created_at >= ? AND created_at <= ? ORDER BY created_at DESC",
        (start_str, end_str)
    ).fetchall())


def get_order_items_by_date_range(start_date, end_date):
    orders = get_orders_by_date_range(start_date, end_date)
    all_items = []
    for o in orders:
        items = get_order_items(o.id)
        for item in items:
            item._data["order_number"] = o._data.get("order_number")
            item._data["order_created_at"] = o._data.get("created_at")
            item._data["pos_order"] = o._data.get("pos_order", 0)
        all_items.extend(items)
    return all_items


def build_report(period_label, start_date, end_date):
    orders = get_orders_by_date_range(start_date, end_date)
    items = get_order_items_by_date_range(start_date, end_date)
    logs = get_logs_by_date_range(start_date, end_date)

    total_orders = len(orders)
    total_rev = sum(o._data.get("total", 0) for o in orders)
    total_items_sold = sum(i._data.get("quantity", 0) for i in items)
    pos_orders = sum(1 for o in orders if o._data.get("pos_order"))
    online_orders = total_orders - pos_orders

    low_stock_count = count_low_stock()
    all_prods = get_all_products(active_only=False)
    total_stock = sum(p._data.get("stock", 0) for p in all_prods)

    product_sales = {}
    for i in items:
        pid = i._data.get("product_id") or i._data.get("product_name", "Unknown")
        name = i._data.get("product_name", "Unknown")
        qty = i._data.get("quantity", 0)
        total = i._data.get("total", 0)
        if pid not in product_sales:
            product_sales[pid] = {"name": name, "quantity": 0, "revenue": 0}
        product_sales[pid]["quantity"] += qty
        product_sales[pid]["revenue"] += total
    top_products = sorted(product_sales.values(), key=lambda x: x["quantity"], reverse=True)[:10]

    cat_breakdown = {}
    for i in items:
        pid = i._data.get("product_id")
        prod = get_product_by_id(pid) if pid else None
        cat_name = "Unknown"
        if prod and prod._data.get("category"):
            cat_name = getattr(prod._data["category"], "name", "Unknown")
        elif prod:
            cid = prod._data.get("category_id")
            cat = get_category_by_id(cid) if cid else None
            cat_name = cat.name if cat else "Unknown"
        if cat_name not in cat_breakdown:
            cat_breakdown[cat_name] = {"quantity": 0, "revenue": 0}
        cat_breakdown[cat_name]["quantity"] += i._data.get("quantity", 0)
        cat_breakdown[cat_name]["revenue"] += i._data.get("total", 0)

    action_counts = {}
    for log in logs:
        act = log._data.get("action", "other")
        action_counts[act] = action_counts.get(act, 0) + 1

    return {
        "period": period_label,
        "start": start_date,
        "end": end_date,
        "total_orders": total_orders,
        "total_revenue": round(total_rev, 2),
        "total_items_sold": total_items_sold,
        "pos_orders": pos_orders,
        "online_orders": online_orders,
        "low_stock_count": low_stock_count,
        "total_stock": total_stock,
        "product_count": len(all_prods),
        "top_products": top_products,
        "category_breakdown": cat_breakdown,
        "log_activity_counts": action_counts,
        "total_logs": len(logs),
        "log_entries": logs[:20],
    }


# ═══════════════════════════════════════════════════════════════
#  SEED
# ═══════════════════════════════════════════════════════════════
def seed_database():
    import bcrypt

    if get_user_by_email("admin@uncleswellness.com"):
        return

    admin_pass = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
    create_user({"name": "Admin", "email": "admin@uncleswellness.com",
                 "password": admin_pass, "role": "admin"})

    cat_data = [
        ("Skincare", "skincare", "Face creams, serums, cleansers & more"),
        ("Haircare", "haircare", "Shampoos, conditioners, hair oils & treatments"),
        ("Makeup", "makeup", "Foundation, lipstick, eyeshadow & cosmetics"),
        ("Fragrance", "fragrance", "Perfumes, body sprays & colognes"),
        ("Bath & Body", "bath-body", "Soaps, lotions, body washes & scrubs"),
        ("Natural & Organic", "natural-organic", "Organic and natural beauty products"),
    ]
    cat_subcats = {
        "skincare": [["Cleansers", "cleansers"], ["Toners", "toners"], ["Serums", "serums"], ["Moisturizers", "moisturizers"], ["Sunscreen", "sunscreen"], ["Face Masks", "face-masks"], ["Eye Care", "eye-care"]],
        "haircare": [["Shampoos", "shampoos"], ["Conditioners", "conditioners"], ["Hair Masks", "hair-masks"], ["Hair Oils", "hair-oils"], ["Leave-in Conditioners", "leave-in-conditioners"], ["Detanglers", "detanglers"], ["Styling Products", "styling-products"]],
        "makeup": [["Foundation", "foundation"], ["Concealer", "concealer"], ["Lipstick", "lipstick"], ["Eyeshadow", "eyeshadow"], ["Mascara", "mascara"], ["Blush", "blush"], ["Setting Spray", "setting-spray"]],
        "fragrance": [["Perfumes", "perfumes"], ["Body Sprays", "body-sprays"], ["Rollerballs", "rollerballs"], ["Gift Sets", "gift-sets"]],
        "bath-body": [["Body Washes", "body-washes"], ["Body Lotions", "body-lotions"], ["Body Scrubs", "body-scrubs"], ["Soaps", "soaps"], ["Bath Bombs", "bath-bombs"], ["Hand Cream", "hand-cream"]],
        "natural-organic": [["Face Oils", "face-oils"], ["Herbal Extracts", "herbal-extracts"], ["Organic Serums", "organic-serums"], ["Natural Supplements", "natural-supplements"]],
    }
    cat_ids = {}
    for name, slug, desc in cat_data:
        cid = create_category({"name": name, "slug": slug, "description": desc,
                               "subcategories": json.dumps(cat_subcats.get(slug, []))})
        cat_ids[slug] = cid

    # (name, slug, desc, price, cost, stock, cat_slug, featured, barcode, subcat_slug)
    products = [
        ("Vitamin C Brightening Serum", "vitamin-c-serum", "Brightening vitamin C serum with hyaluronic acid", 34.99, 18.00, 50, "skincare", True, "BC4001", "serums"),
        ("Hydrating Hyaluronic Acid Moisturizer", "hyaluronic-moisturizer", "Deep hydration moisturizer with hyaluronic acid", 42.99, 22.00, 35, "skincare", True, "BC4002", "moisturizers"),
        ("Retinol Night Cream", "retinol-night-cream", "Anti-aging retinol night cream with vitamin E", 54.99, 28.00, 25, "skincare", False, "BC4003", "moisturizers"),
        ("Gentle Foaming Facial Cleanser", "foaming-cleanser", "Gentle foaming cleanser for all skin types", 24.99, 12.00, 60, "skincare", False, "BC4004", "cleansers"),
        ("Niacinamide 10% + Zinc 1% Serum", "niacinamide-serum", "Oil control serum with niacinamide and zinc", 29.99, 15.00, 40, "skincare", True, "BC4005", "serums"),
        ("Argan Oil Hair Treatment", "argan-oil-hair", "Moroccan argan oil for silky, frizz-free hair", 19.99, 9.00, 45, "haircare", True, "BC4006", "hair-oils"),
        ("Keratin Smoothing Shampoo", "keratin-shampoo", "Keratin-infused shampoo for smooth hair", 16.99, 8.00, 70, "haircare", False, "BC4007", "shampoos"),
        ("Biotin Hair Growth Serum", "biotin-hair-serum", "Biotin and castor oil serum for hair growth", 27.99, 14.00, 30, "haircare", False, "BC4008", "hair-oils"),
        ("Coconut & Shea Conditioner", "coconut-conditioner", "Nourishing conditioner with coconut oil and shea butter", 18.99, 9.00, 55, "haircare", False, "BC4009", "conditioners"),
        ("Longwear Liquid Foundation", "liquid-foundation", "Full coverage liquid foundation with SPF 20", 38.99, 19.00, 40, "makeup", True, "BC4010", "foundation"),
        ("Matte Lipstick Collection", "matte-lipstick", "Long-lasting matte lipstick, 12-hour wear", 22.99, 11.00, 65, "makeup", False, "BC4011", "lipstick"),
        ("Eyeshadow Palette 24 Colors", "eyeshadow-palette", "24-shade palette with matte and shimmer finishes", 45.99, 23.00, 20, "makeup", True, "BC4012", "eyeshadow"),
        ("Waterproof Eyeliner Pen", "waterproof-eyeliner", "Precision waterproof eyeliner pen", 14.99, 7.00, 80, "makeup", False, "BC4013", "eyeshadow"),
        ("Rose Garden Perfume", "rose-perfume", "Elegant rose fragrance with jasmine and sandalwood", 64.99, 32.00, 15, "fragrance", True, "BC4014", "perfumes"),
        ("Vanilla Bean Body Spray", "vanilla-body-spray", "Warm vanilla body spray for everyday freshness", 16.99, 8.00, 90, "fragrance", False, "BC4015", "body-sprays"),
        ("Citrus Burst Eau de Toilette", "citrus-edt", "Refreshing citrus eau de toilette", 48.99, 24.00, 25, "fragrance", False, "BC4016", "perfumes"),
        ("Shea Butter Body Lotion", "shea-butter-lotion", "Ultra-moisturizing shea butter body lotion", 21.99, 10.00, 50, "bath-body", False, "BC4017", "body-lotions"),
        ("Exfoliating Coffee Body Scrub", "coffee-body-scrub", "Natural coffee grounds body scrub", 18.99, 9.00, 35, "bath-body", False, "BC4018", "body-scrubs"),
        ("Lavender Bath Bombs Set", "lavender-bath-bombs", "Set of 6 lavender-scented bath bombs", 26.99, 13.00, 40, "bath-body", True, "BC4019", "bath-bombs"),
        ("Charcoal Detox Face Mask", "charcoal-face-mask", "Activated charcoal mask for deep pore cleansing", 15.99, 7.00, 60, "skincare", False, "BC4020", "face-masks"),
        ("Organic Rosehip Oil", "rosehip-oil", "Cold-pressed organic rosehip oil for skin regeneration", 28.99, 15.00, 30, "natural-organic", True, "BC4021", "face-oils"),
        ("Aloe Vera Gel 99% Pure", "aloe-vera-gel", "Pure organic aloe vera gel for soothing skin", 13.99, 6.00, 75, "natural-organic", False, "BC4022", "face-oils"),
        ("Tea Tree Oil Acne Treatment", "tea-tree-acne", "Organic tea tree oil spot treatment for acne", 16.99, 8.00, 55, "natural-organic", False, "BC4023", "herbal-extracts"),
        ("Silk Hair Wrap Turban", "silk-hair-wrap", "Microfiber silk hair wrap for fast drying", 12.99, 6.00, 100, "haircare", False, "BC4024", "styling-products"),
    ]
    for name, slug, desc, price, cost, stock, cat_slug, featured, barcode, subcat_slug in products:
        subcat_name = ""
        for sc in cat_subcats.get(cat_slug, []):
            if sc[1] == subcat_slug:
                subcat_name = sc[0]
                break
        create_product({"name": name, "slug": slug, "description": desc,
                        "price": price, "cost_price": cost, "stock": stock,
                        "category_id": cat_ids[cat_slug],
                        "subcategory": subcat_name, "subcategory_slug": subcat_slug,
                        "featured": (1 if featured else 0),
                        "barcode": barcode})