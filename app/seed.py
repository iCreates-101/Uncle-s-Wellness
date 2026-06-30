"""Standalone seed script — run with: python seed.py

Requires Firebase credentials (see firebase_db.py for setup).
"""
from app.firebase_db import init_firebase, seed_database

init_firebase()
seed_database()
print("Database seeded!  Admin: admin@uncleswellness.com / admin123")
