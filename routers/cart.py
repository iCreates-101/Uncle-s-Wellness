import datetime
import random
import string

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse

from firebase_db import (
    get_cart_items, add_cart_item, update_cart_quantity, remove_cart_item
)
from templates import templates
from utils import get_common_context

router = APIRouter()


@router.post("/cart/add")
def cart_add(request: Request, product_id: str = Form(...), quantity: int = Form(1)):
    if "session_id" not in request.session:
        request.session["session_id"] = ("sess_" +
            datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S") + "_" +
            "".join(random.choices(string.ascii_lowercase + string.digits, k=8)))
    sid = request.session["session_id"]
    add_cart_item(sid, product_id, quantity)
    ref = request.headers.get("referer", "/cart")
    return RedirectResponse(ref, status_code=302)


@router.post("/cart/update")
def cart_update(request: Request, id: str = Form(...), quantity: int = Form(...)):
    update_cart_quantity(id, quantity)
    return RedirectResponse("/cart", status_code=302)


@router.post("/cart/remove")
def cart_remove(request: Request, id: str = Form(...)):
    remove_cart_item(id)
    return RedirectResponse("/cart", status_code=302)


@router.get("/cart")
def cart_page(request: Request):
    ctx = get_common_context(request)
    sid = request.session.get("session_id")
    items = []
    subtotal = 0.0
    if sid:
        items = get_cart_items(sid)
        for item in items:
            item.total_price = item._data.get("price", 0) * item._data.get("quantity", 0)
            subtotal += item.total_price
    ctx["items"] = items
    ctx["subtotal"] = subtotal
    return templates.TemplateResponse("cart.html", ctx)
