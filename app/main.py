import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.routers import admin, auth, cart, orders
from app.firebase_db import init_firebase, get_db, seed_database as fb_seed

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(title="Uncle's Wellness", debug=os.getenv("DEBUG", "false").lower() == "true")
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET_KEY", "uncle-wellness-secret-key-2024"))
app.mount("/static", StaticFiles(directory=os.path.join(_PROJECT_ROOT, "static")), name="static")

from app.routers import shop
app.include_router(auth.router)
app.include_router(shop.router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(admin.router)


@app.on_event("startup")
def startup():
    init_firebase()
    # Auto-seed if no products exist
    from app.firebase_db import get_all_products
    if len(get_all_products(active_only=False)) == 0:
        fb_seed()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=True)
