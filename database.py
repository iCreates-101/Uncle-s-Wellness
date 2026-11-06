"""Database layer — delegates to Supabase (or SQLite fallback)."""
from supabase_db import init_db, get_db, seed_database
from supabase_db import init_db as init_firebase  # backward-compatible alias

__all__ = ["init_db", "init_firebase", "get_db", "seed_database"]
