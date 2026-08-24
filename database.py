"""Database layer — delegates to Firebase Firestore."""
from firebase_db import init_firebase, get_db, seed_database

__all__ = ["init_firebase", "get_db", "seed_database"]
