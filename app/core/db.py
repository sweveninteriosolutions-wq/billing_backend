from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import DATABASE_URL
from sqlalchemy import event

# -----------------------
# Async engine
# -----------------------
engine = create_async_engine(
    DATABASE_URL,
    echo=False,   # True for debug SQL logs
    future=True,  # SQLAlchemy 2.0 style
)

# -----------------------
# Async session factory
# -----------------------
AsyncSessionLocal: sessionmaker[AsyncSession] = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)

# -----------------------
# Base class for models
# -----------------------
Base = declarative_base()


# -----------------------
# FastAPI dependency
# -----------------------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Async generator to provide a DB session.
    Use with `Depends(get_db)` in FastAPI routes.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Enable foreign key support for SQLite
@event.listens_for(engine.sync_engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# -----------------------
# Optional: helper to create all tables (like Django migrate)
# -----------------------
async def init_models():
    """
    Call this on startup to create all tables defined in your models.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
