from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event
from app.config import settings

class Base(DeclarativeBase):
    pass

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args=connect_args
)

# Enable WAL mode and foreign keys for SQLite
if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Безопасная автомиграция для SQLite при добавлении новых полей
        if settings.DATABASE_URL.startswith("sqlite"):
            def migrate_columns(connection):
                cursor = connection.cursor()
                try:
                    cursor.execute("PRAGMA table_info(masters)")
                    existing_cols = [row[1] for row in cursor.fetchall()]
                    if existing_cols and "salon_name" not in existing_cols:
                        cursor.execute("ALTER TABLE masters ADD COLUMN salon_name VARCHAR(150)")
                    if existing_cols and "address" not in existing_cols:
                        cursor.execute("ALTER TABLE masters ADD COLUMN address VARCHAR(255)")
                except Exception:
                    pass
                finally:
                    cursor.close()

            await conn.run_sync(migrate_columns)
