import os
from dotenv import load_dotenv

load_dotenv()

DB_TYPE = os.getenv("DB_TYPE", "sqlite")  # or "postgres"

if DB_TYPE == "postgres":
    DATABASE_URL = os.getenv("DATABASE_URL")
else:
    DATABASE_URL = "sqlite+aiosqlite:///./test.db"

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise ValueError("JWT_SECRET environment variable must be set")
JWT_ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 15          # For cashiers/sales/inventory
ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES = 60    # Admin access token
REFRESH_TOKEN_EXPIRE_DAYS = 7             # Only admins get refresh tokens
