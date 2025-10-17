from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
from app.core.config import JWT_SECRET, JWT_ALGORITHM
from typing import Any


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    # bcrypt can only handle first 72 bytes
    password_bytes = password.encode("utf-8")[:72]
    password_safe = password_bytes.decode("utf-8", "ignore")
    return pwd_context.hash(password_safe)

def verify_password(plain: str, hashed: str) -> bool:
    plain_bytes = plain.encode("utf-8")[:72]
    plain_safe = plain_bytes.decode("utf-8", "ignore")
    return pwd_context.verify(plain_safe, hashed)

def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def create_refresh_token(data: dict, expires_delta: timedelta = timedelta(days=7)):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)