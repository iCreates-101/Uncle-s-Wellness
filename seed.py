"""Standalone seed script — run with: python seed.py

Seeds Supabase (or the local SQLite fallback) with demo data.
"""
from supabase_db import init_db, seed_database

init_db()
seed_database()
print("Database seeded!  Admin: admin@uncleswellness.com / admin123")
