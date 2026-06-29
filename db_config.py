import os

DATABASE_URL = os.environ.get("DATABASE_URL", None)
USE_POSTGRES = DATABASE_URL is not None


def ph():
    """SQL placeholder: %s for PostgreSQL, ? for SQLite."""
    return "%s" if USE_POSTGRES else "?"
