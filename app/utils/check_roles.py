# app/utils/check_roles.py
from fastapi import HTTPException
from typing import Callable
from functools import wraps


def require_role(roles: list[str]):
    """Decorator to validate user role; expects user to be passed by route."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, _user, **kwargs):
            if _user is None:
                raise HTTPException(status_code=401, detail="User not authenticated")
            if _user.role.lower() not in [r.lower() for r in roles]:
                raise HTTPException(status_code=403, detail="Permission denied")
            return await func(*args, _user=_user, **kwargs)
        return wrapper
    return decorator