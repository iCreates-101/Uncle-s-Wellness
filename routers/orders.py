from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse

from firebase_db import (
    get_cart_items, clear_cart, get_product_by_id, get_order_by_id,
    create_order, get_orders_by_user, get_order_items, create_order_item
)
from firebase_db import update_product as fb_update_product
from templates import templates
from utils import get_common_context, require_auth, gen_order_number

router = APIRouter()


@router.get("/checkout")
def checkout_page(request: Request):
    ctx = get_common_context(request)
    sid = request.session.get("session_id")
    items = []
    subtotal = 0.0
    if sid:
        items = get_cart_items(sid, active_only=False)
        for item in items:
            subtotal += item._data.get("price", 0) * item._data.get("quantity", 0)
    if not items:
        return RedirectResponse("/cart", status_code=302)
    ctx["items"] = items
    ctx["subtotal"] = subtotal
    ctx["error"] = None
    return templates.TemplateResponse("checkout.html", ctx)


@router.post("/checkout")
def checkout_post(request: Request,
                  customer_name: str = Form(...),
                  customer_email: str = Form(...),
                  customer_phone: str = Form(...),
                  shipping_address: str = Form(...),
                  payment_method: str = Form("cod"),
                  notes: str = Form("")):
    ctx = get_common_context(request)
    sid = request.session.get("session_id")
    cart_items = get_cart_items(sid, active_only=False)

    items = []
    subtotal = 0.0
    for item in cart_items:
        prod = get_product_by_id(item.product_id)
        if not prod:
            continue
        qty = item._data.get("quantity", 0)
        if prod._data.get("stock", 0) < qty:
            ctx["error"] = f"Insufficient stock for {prod.name}"
            ctx["items"] = cart_items
            ctx["subtotal"] = subtotal
            return templates.TemplateResponse("checkout.html", ctx)
        total = round(prod.price * qty, 2)
        subtotal += total
        items.append({"product_id": prod.id, "name": prod.name,
                      "price": prod.price, "quantity": qty, "total": total})

    if not items:
        return RedirectResponse("/cart", status_code=302)

    shipping = 0 if subtotal >= 50 else 5.99
    tax = round(subtotal * 0.08, 2)
    total = round(subtotal + shipping + tax, 2)
    order_number = gen_order_number()
    user_id = request.session.get("user", {}).get("id")

    order_id = create_order({
        "order_number": order_number,
        "user_id": user_id,
        "customer_name": customer_name,
        "customer_email": customer_email,
        "customer_phone": customer_phone,
        "shipping_address": shipping_address,
        "payment_method": payment_method,
        "subtotal": subtotal,
        "shipping": shipping,
        "tax": tax,
        "total": total,
        "order_status": "confirmed",
        "payment_status": "paid",
        "notes": notes,
    })

    for item in items:
        create_order_item({
            "order_id": order_id,
            "product_id": item["product_id"],
            "product_name": item["name"],
            "price": item["price"],
            "quantity": item["quantity"],
            "total": item["total"],
        })
        prod = get_product_by_id(item["product_id"])
        if prod:
            fb_update_product(prod.id, {"stock": prod._data.get("stock", 0) - item["quantity"]})

    clear_cart(sid)
    return RedirectResponse(f"/order-confirmation/{order_id}", status_code=302)


@router.get("/order-confirmation/{order_id}")
def order_confirmation(order_id: str, request: Request):
    ctx = get_common_context(request)
    order = get_order_by_id(order_id)
    if not order:
        return RedirectResponse("/", status_code=302)
    ctx["order"] = order
    ctx["items"] = get_order_items(order_id)
    return templates.TemplateResponse("order-confirmation.html", ctx)


@router.get("/orders")
def my_orders(request: Request):
    if not require_auth(request):
        request.session["return_to"] = "/orders"
        return RedirectResponse("/login", status_code=302)
    ctx = get_common_context(request)
    user_id = request.session["user"]["id"]
    ctx["orders"] = get_orders_by_user(user_id)
    return templates.TemplateResponse("orders.html", ctx)


@router.get("/order/{order_id}")
def order_detail(order_id: str, request: Request):
    if not require_auth(request):
        return RedirectResponse("/login", status_code=302)
    ctx = get_common_context(request)
    user_id = request.session["user"]["id"]
    order = get_order_by_id(order_id)
    if not order or order._data.get("user_id") != user_id:
        return RedirectResponse("/orders", status_code=302)
    ctx["order"] = order
    ctx["items"] = get_order_items(order_id)
    return templates.TemplateResponse("order-detail.html", ctx)
