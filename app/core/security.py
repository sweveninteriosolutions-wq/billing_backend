from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
from app.core.config import JWT_SECRET, JWT_ALGORITHM


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_token(data: dict, expires_delta: timedelta, secret: str, algorithm: str) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, secret, algorithm=algorithm)
def create_access_token(data: dict, expires_delta: timedelta) -> str:
    return _create_token(data, expires_delta, JWT_SECRET, JWT_ALGORITHM)

def create_refresh_token(data: dict, expires_delta: timedelta = timedelta(days=7)) -> str:
    return _create_token(data, expires_delta, JWT_SECRET, JWT_ALGORITHM)