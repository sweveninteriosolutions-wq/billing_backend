from app.models.user_models import User
from app.core.db import AsyncSessionLocal
from app.core.security import hash_password
import asyncio

async def create_admin():
    async with AsyncSessionLocal() as session:
        admin = User(
            username="admin",
            password_hash=hash_password("admin123"),
            role="admin",
            is_active=True
        )
        session.add(admin)
        await session.commit()
        print("Admin user created!")

asyncio.run(create_admin())
