# app/middleware/activity_logger.py
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.utils.activity_helpers import log_user_activity
from app.core.db import get_db

class ActivityLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Get user info
        user = getattr(request.state, "user", None)
        user_id = getattr(user, "id", None) if user else None
        username = getattr(user, "username", None) if user else None

        # Call actual endpoint
        response = await call_next(request)

        # Only log POST, PUT, DELETE (modify) requests
        if user_id and request.method in ["POST", "PUT", "DELETE"]:
            # Default message
            message = f"Performed {request.method} on {request.url.path}"

            # If the response provides a custom activity message
            if hasattr(response, "activity_message"):
                message = response.activity_message

            # Save activity asynchronously
            try:
                async for db in get_db():  # iterate async generator
                    await log_user_activity(db, user_id=user_id, username=username, message=message)
            except Exception as e:
                print("Failed to log activity:", e)

        return response
