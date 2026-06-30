from fastapi import APIRouter, Request, Query, Depends
from fastapi.responses import RedirectResponse

from app.firebase_db import (
    get_all_products, search_products, get_product_by_slug,
    get_related_products, get_category_by_slug, get_all_categories
)
from app.templates import templates
from app.utils import get_common_context

router = APIRouter()


@router.get("/")
def home(request: Request):
    ctx = get_common_context(request)
    ctx["featured"] = get_all_products(active_only=True, featured=True,
                                       sort_by="created_at", limit_val=8)
    return templates.TemplateResponse("index.html", ctx)


@router.get("/shop")
def shop(request: Request, category: str = Query(None), search: str = Query(None),
         sort: str = Query(None), subcategory: str = Query(None)):
    ctx = get_common_context(request)

    if search:
        products = search_products(search)
    else:
        cat_id = None
        if category:
            cat = get_category_by_slug(category)
            if cat:
                cat_id = cat.id
        sort_map = {"price_asc": ("price", "asc"), "price_desc": ("price", "desc"),
                    "name": ("name", "asc"), "newest": ("created_at", "desc")}
        sort_by, sort_dir = sort_map.get(sort, ("created_at", "desc"))
        products = get_all_products(active_only=True, category=cat_id,
                                    sort_by=sort_by, sort_dir=sort_dir,
                                    subcategory=subcategory)

    ctx["products"] = products
    ctx["currentCategory"] = category or ""
    ctx["currentSearch"] = search or ""
    ctx["currentSort"] = sort or ""
    ctx["currentSubcategory"] = subcategory or ""
    return templates.TemplateResponse("shop.html", ctx)


@router.get("/product/{slug}")
def product_detail(slug: str, request: Request):
    ctx = get_common_context(request)
    product = get_product_by_slug(slug)
    if not product:
        return RedirectResponse("/shop", status_code=302)
    ctx["product"] = product
    ctx["related"] = get_related_products(product._data.get("category_id"),
                                          product.id, limit_val=4)
    return templates.TemplateResponse("product.html", ctx)
