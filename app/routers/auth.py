from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
import bcrypt

from app.firebase_db import get_user_by_email, create_user
from app.templates import templates
from app.utils import get_common_context

router = APIRouter()


@router.get("/login")
def login_page(request: Request):
    if request.session.get("user"):
        return RedirectResponse("/", status_code=302)
    ctx = {"request": request, "error": None, "user": None, "cartCount": 0, "categories": []}
    return templates.TemplateResponse("login.html", ctx)


@router.post("/login")
def login_post(request: Request, email: str = Form(...), password: str = Form(...)):
    user = get_user_by_email(email)
    if not user or not bcrypt.checkpw(password.encode(), user.password.encode()):
        ctx = {"request": request, "error": "Invalid email or password", "user": None, "cartCount": 0, "categories": []}
        return templates.TemplateResponse("login.html", ctx)
    request.session["user"] = {"id": user.id, "name": user.name, "email": user.email, "role": user.role}
    return_to = request.session.get("return_to", "/")
    return RedirectResponse(return_to, status_code=302)


@router.get("/register")
def register_page(request: Request):
    if request.session.get("user"):
        return RedirectResponse("/", status_code=302)
    ctx = {"request": request, "error": None, "user": None, "cartCount": 0, "categories": []}
    return templates.TemplateResponse("register.html", ctx)


@router.post("/register")
def register_post(request: Request, name: str = Form(...), email: str = Form(...),
                  password: str = Form(...), confirm_password: str = Form(...)):
    ctx = {"request": request, "user": None, "cartCount": 0, "categories": []}
    if not name or not email or not password:
        ctx["error"] = "All fields required"
        return templates.TemplateResponse("register.html", ctx)
    if password != confirm_password:
        ctx["error"] = "Passwords do not match"
        return templates.TemplateResponse("register.html", ctx)
    if len(password) < 6:
        ctx["error"] = "Password must be at least 6 characters"
        return templates.TemplateResponse("register.html", ctx)
    if get_user_by_email(email):
        ctx["error"] = "Email already registered"
        return templates.TemplateResponse("register.html", ctx)

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    create_user({"name": name, "email": email, "password": hashed, "role": "customer"})
    return RedirectResponse("/login", status_code=302)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=302)
