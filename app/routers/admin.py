from fastapi import APIRouter, Request, Form, Query, Depends
from fastapi.responses import RedirectResponse, JSONResponse

from app.firebase_db import (
    get_product_by_id, get_product_by_slug, get_all_products, search_products,
    create_product, update_product, delete_product,
    get_all_categories, get_category_by_slug, get_category_by_id,
    create_category, delete_category,
    get_all_orders, get_order_by_id, get_order_by_number,
    get_order_items, get_recent_orders, update_order,
    get_pos_orders, get_inventory,
    count_products, count_low_stock, count_orders, total_revenue,
    count_users, get_user_by_email, create_order_item,
    create_log, get_logs, build_report,
    seed_database as fb_seed,
)
import datetime
from app.templates import templates
from app.utils import get_common_context, require_admin, make_slug, gen_order_number

router = APIRouter()


# ─── Dashboard ──────────────────────────────────────────────────
@router.get("/admin")
def admin_dashboard(request: Request):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=302)
    ctx = get_common_context(request)
    ctx["stats"] = {
        "products": count_products(),
        "orders": count_orders(),
        "revenue": total_revenue(),
        "customers": count_users(),
        "lowStock": count_low_stock(),
        "recentOrders": get_recent_orders(),
    }
    return templates.TemplateResponse("admin/dashboard.html", ctx)


# ─── Products ───────────────────────────────────────────────────
@router.get("/admin/products")
def admin_products(request: Request):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=302)
    ctx = get_common_context(request)
    ctx["products"] = get_all_products(active_only=False, sort_by="created_at")
    return templates.TemplateResponse("admin/products.html", ctx)


@router.get("/admin/products/new")
def admin_product_new_form(request: Request):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=302)
    ctx = get_common_context(request)
    ctx["product"] = None
    ctx["categories"] = get_all_categories()
    return templates.TemplateResponse("admin/product-form.html", ctx)


@router.post("/admin/products/new")
def admin_product_new(request: Request,
                      name: str = Form(...), description: str = Form(""),
                      price: float = Form(...), cost_price: float = Form(0),
                      stock: int = Form(0), category_id: str = Form(""),
                      featured: int = Form(0), barcode: str = Form("")):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=302)
    slug = make_slug(name)
    create_product({
        "name": name, "slug": slug, "description": description,
        "price": price, "cost_price": cost_price, "stock": stock,
        "category_id": category_id, "featured": featured,
        "barcode": barcode or None,
    })
    user = request.session.get("user", {})
    create_log("product_create", f"Created product '{name}'", user.get("id"), user.get("name"), "product", None)
    return RedirectResponse("/admin/products", status_code=302)


@router.get("/admin/products/edit/{product_id}")
def admin_product_edit_form(product_id: str, request: Request):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=302)
    ctx = get_common_context(request)
    ctx["product"] = get_product_by_id(product_id)
    ctx["categories"] = get_all_categories()
    if not ctx["product"]:
        return RedirectResponse("/admin/products", status_code=302)
    return templates.TemplateResponse("admin/product-form.html", ctx)


@router.post("/admin/products/edit/{product_id}")
def admin_product_edit(product_id: str, request: Request,
                       name: str = Form(...), description: str = Form(""),
                       price: float = Form(...), cost_price: float = Form(0),
                       stock: int = Form(0), category_id: str = Form(""),
                       featured: int = Form(0), barcode: str = Form("")):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=302)
    slug = make_slug(name)
    update_product(product_id, {
        "name": name, "slug": slug, "description": description,
        "price": price, "cost_price": cost_price, "stock": stock,
        "category_id": category_id, "featured": featured,
        "barcode": barcode or None,
    })
    user = request.session.get("user", {})
    create_log("product_update", f"Updated product '{name}'", user.get("id"), user.get("name"), "product", product_id)
    return RedirectResponse("/admin/products", status_code=302)


@router.post("/admin/products/delete/{product_id}")
def admin_product_delete(product_id: str, request: Request):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=302)
    prod = get_product_by_id(product_id)
    name = prod.name if prod else product_id
    delete_product(product_id)
    user = request.session.get("user", {})
    create_log("product_delete", f"Deleted product '{name}'", user.get("id"), user.get("name"), "product", product_id)
    return RedirectResponse("/admin/products", status_code=302)


# ─── Orders ─────────────────────────────────────────────────────
@router.get("/admin/orders")
def admin_orders(request: Request, status: str = Query(None)):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=302)
    ctx = get_common_context(request)
    ctx["orders"] = get_all_orders(status=status)
    ctx["currentStatus"] = status or ""
    return templates.TemplateResponse("admin/orders.html", ctx)


@router.get("/admin/orders/{order_id}")
def admin_order_detail(order_id: str, request: Request):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=302)
    ctx = get_common_context(request)
    ctx["order"] = get_order_by_id(order_id)
    if not ctx["order"]:
        return RedirectResponse("/admin/orders", status_code=302)
    ctx["items"] = get_order_items(order_id)
    return templates.TemplateResponse("admin/order-detail.html", ctx)


@router.post("/admin/orders/{order_id}/status")
def admin_order_status(order_id: str, request: Request,
                       order_status: str = Form(None),
                       payment_status: str = Form(None)):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=302)
    upd = {}
    if order_status:
        upd["order_status"] = order_status
    if payment_status:
        upd["payment_status"] = payment_status
    if upd:
        update_order(order_id, upd)
        user = request.session.get("user", {})
        desc = f"Updated order {get_order_by_id(order_id).order_number}: {', '.join(f'{k}={v}' for k,v in upd.items())}"
        create_log("order_update", desc, user.get("id"), user.get("name"), "order", order_id)
    return RedirectResponse(f"/admin/orders/{order_id}", status_code=302)


# ─── Categories ─────────────────────────────────────────────────
@router.get("/admin/categories")
def admin_categories(request: Request):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=302)
    ctx = get_common_context(request)
    cats = get_all_categories()
    for c in cats:
        c.product_count = len(get_all_products(active_only=False, category=c.id))
    ctx["categories"] = cats
    return templates.TemplateResponse("admin/categories.html", ctx)


@router.post("/admin/categories/new")
def admin_category_new(request: Request, name: str = Form(...),
                       description: str = Form("")):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=302)
    slug = make_slug(name)
    create_category({"name": name, "slug": slug, "description": description})
    user = request.session.get("user", {})
    create_log("category_create", f"Created category '{name}'", user.get("id"), user.get("name"), "category", None)
    return RedirectResponse("/admin/categories", status_code=302)


@router.post("/admin/categories/delete/{category_id}")
def admin_category_delete(category_id: str, request: Request):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=302)
    cat = get_category_by_id(category_id)
    name = cat.name if cat else category_id
    delete_category(category_id)
    user = request.session.get("user", {})
    create_log("category_delete", f"Deleted category '{name}'", user.get("id"), user.get("name"), "category", category_id)
    return RedirectResponse("/admin/categories", status_code=302)


# ─── Inventory ──────────────────────────────────────────────────
@router.get("/admin/inventory")
def admin_inventory(request: Request):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=302)
    ctx = get_common_context(request)
    ctx["products"] = get_inventory()
    return templates.TemplateResponse("admin/inventory.html", ctx)


@router.post("/admin/inventory/update/{product_id}")
def admin_inventory_update(product_id: str, request: Request,
                           stock: int = Form(...)):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=302)
    update_product(product_id, {"stock": stock})
    prod = get_product_by_id(product_id)
    user = request.session.get("user", {})
    create_log("inventory_update", f"Updated stock for '{prod.name if prod else product_id}' to {stock}", user.get("id"), user.get("name"), "product", product_id)
    return RedirectResponse("/admin/inventory", status_code=302)


# ═══════════════════════════════════════════════════════════════════
#  POS SYSTEM
# ═══════════════════════════════════════════════════════════════════
@router.get("/admin/pos")
def pos_terminal(request: Request):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=302)
    ctx = get_common_context(request)
    ctx["products"] = get_all_products(active_only=True, sort_by="name")
    ctx["categories"] = get_all_categories()
    return templates.TemplateResponse("admin/pos.html", ctx)


@router.get("/admin/pos/search")
def pos_search(q: str = Query("")):
    if not q.strip():
        return JSONResponse([])
    results = search_products(q)
    return JSONResponse([{
        "id": p.id, "name": p.name, "price": p.price, "stock": p.stock,
        "barcode": p._data.get("barcode"),
        "category_name": p._data.get("category", {}).get("name") if p._data.get("category") else "",
    } for p in results])


@router.get("/admin/pos/product/{barcode}")
def pos_product_by_barcode(barcode: str):
    from app.firebase_db import get_product_by_barcode
    product = get_product_by_barcode(barcode)
    if not product:
        return JSONResponse(None)
    return JSONResponse({"id": product.id, "name": product.name, "price": product.price,
                         "stock": product.stock, "barcode": product._data.get("barcode")})


@router.post("/admin/pos/checkout")
async def pos_checkout(request: Request):
    if not require_admin(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    data = await request.json()
    items_data = data.get("items", [])
    payment_method = data.get("payment_method", "cash")
    customer_name = data.get("customer_name", "Walk-in Customer")
    customer_phone = data.get("customer_phone", "")
    amount_tendered = data.get("amount_tendered")
    notes = data.get("notes", "")

    if not items_data:
        return JSONResponse({"error": "No items in cart"}, status_code=400)

    order_items = []
    subtotal = 0.0
    for item_data in items_data:
        prod = get_product_by_id(item_data["id"])
        if not prod:
            return JSONResponse({"error": f"Product ID {item_data['id']} not found"}, status_code=400)
        if prod._data.get("stock", 0) < item_data["quantity"]:
            return JSONResponse({"error": f"Insufficient stock for {prod.name}"}, status_code=400)
        total = round(prod.price * item_data["quantity"], 2)
        subtotal += total
        order_items.append({
            "product_id": prod.id,
            "product_name": prod.name,
            "price": prod.price,
            "quantity": item_data["quantity"],
            "total": total,
        })

    tax = round(subtotal * 0.08, 2)
    total = round(subtotal + tax, 2)
    change = round(float(amount_tendered) - total, 2) if amount_tendered else 0
    order_number = gen_order_number("POS")
    uid = request.session.get("user", {}).get("id")

    oid = create_order({
        "order_number": order_number,
        "user_id": uid,
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "payment_method": payment_method,
        "subtotal": subtotal,
        "tax": tax,
        "total": total,
        "order_status": "completed",
        "payment_status": "paid",
        "notes": notes,
        "pos_order": 1,
    })

    for oi in order_items:
        create_order_item({
            "order_id": oid,
            "product_id": oi["product_id"],
            "product_name": oi["product_name"],
            "price": oi["price"],
            "quantity": oi["quantity"],
            "total": oi["total"],
        })
        update_product(oi["product_id"], {"stock": get_product_by_id(oi["product_id"])._data.get("stock", 0) - oi["quantity"]})

    return JSONResponse({
        "success": True, "order_id": oid, "order_number": order_number,
        "subtotal": subtotal, "tax": tax, "total": total,
        "amount_tendered": float(amount_tendered) if amount_tendered else total,
        "change": change, "items": order_items, "customer_name": customer_name,
    })


@router.get("/admin/pos/receipt/{order_id}")
def pos_receipt(order_id: str, request: Request):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=302)
    ctx = get_common_context(request)
    ctx["order"] = get_order_by_id(order_id)
    if not ctx["order"]:
        return RedirectResponse("/admin/pos", status_code=302)
    ctx["items"] = get_order_items(order_id)
    return templates.TemplateResponse("admin/receipt.html", ctx)


@router.get("/admin/pos/history")
def pos_history(request: Request):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=302)
    ctx = get_common_context(request)
    ctx["orders"] = get_pos_orders()
    return templates.TemplateResponse("admin/pos-history.html", ctx)


# ─── Activity Logs ─────────────────────────────────────────────
@router.get("/admin/logs")
def admin_logs(request: Request):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=302)
    ctx = get_common_context(request)
    ctx["logs"] = get_logs(limit_val=200)
    return templates.TemplateResponse("admin/logs.html", ctx)


# ─── Reports ────────────────────────────────────────────────────
@router.get("/admin/reports")
def admin_reports(request: Request, period: str = Query("quarterly")):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=302)
    now = datetime.datetime.utcnow()
    if period == "yearly":
        start = now - datetime.timedelta(days=365)
        label = "Past Year"
    elif period == "six_months":
        start = now - datetime.timedelta(days=180)
        label = "Past 6 Months"
    else:
        start = now - datetime.timedelta(days=90)
        label = "Past 3 Months (Quarterly)"
    ctx = get_common_context(request)
    ctx["report"] = build_report(label, start, now)
    ctx["currentPeriod"] = period
    return templates.TemplateResponse("admin/reports.html", ctx)


# ─── Reseed (convenience for dev) ───────────────────────────────
@router.post("/admin/reseed")
def admin_reseed(request: Request):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=302)
    fb_seed()
    return RedirectResponse("/admin", status_code=302)
