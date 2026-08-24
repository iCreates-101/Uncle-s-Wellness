import datetime
import json
import random
import string

from fastapi import Request

from firebase_db import get_all_categories, get_cart_count


def get_common_context(request: Request, _db=None):
    user = request.session.get("user")
    session_id = request.session.get("session_id")
    cart_count = get_cart_count(session_id) if session_id else 0
    categories = get_all_categories()
    # Parse JSON subcategories on each category into a .parsed_subcats attr
    for c in categories:
        raw = c._data.get("subcategories", "[]")
        if isinstance(raw, str):
            c._data["parsed_subcats"] = json.loads(raw)
        else:
            c._data["parsed_subcats"] = raw if isinstance(raw, list) else []
    return {
        "request": request,
        "user": user,
        "cartCount": cart_count,
        "categories": categories,
    }


def require_admin(request: Request):
    user = request.session.get("user")
    if not user or user.get("role") != "admin":
        return False
    return True


def require_auth(request: Request):
    return request.session.get("user") is not None


def make_slug(name):
    slug = name.lower().strip()
    for ch in "[]{}()&$%@!#^*,.:;\"'":
        slug = slug.replace(ch, "")
    slug = "-".join(slug.split())
    slug = "".join(c for c in slug if c.isalnum() or c == "-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


def gen_order_number(prefix="ORD"):
    ts = datetime.datetime.utcnow().strftime("%y%m%d%H%M%S")
    rand = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{prefix}-{ts}-{rand}"
