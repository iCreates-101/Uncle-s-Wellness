import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from firebase_db import init_firebase, seed_database as fb_seed

app = FastAPI(title="Uncle's Wellness")

# CORS — required when frontend and backend are deployed on separate origins
_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

secret_key = os.getenv("SESSION_SECRET_KEY", "uncle-wellness-secret-key-2024")
app.add_middleware(SessionMiddleware, secret_key=secret_key)
app.mount("/static", StaticFiles(directory="static"), name="static")

from routers import auth, shop, cart, orders, admin
app.include_router(auth.router)
app.include_router(shop.router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(admin.router)


@app.on_event("startup")
def startup():
    init_firebase()
    from firebase_db import get_all_products
    if len(get_all_products(active_only=False)) == 0:
        fb_seed()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=True)
