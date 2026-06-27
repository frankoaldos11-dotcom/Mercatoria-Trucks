import os

DATABASE_URL = os.environ.get("DATABASE_URL", None)
USE_POSTGRES = DATABASE_URL is not None
