"""
Database Configuration and Session Management
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator

from app.core.config import settings


class Base(DeclarativeBase):
    """Base class for all models"""
    pass


# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True
)

# Create session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database sessions"""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables and create admin user"""
    from app.models.user import User
    from app.models.audit import AuditLog
    from app.core.security import get_password_hash
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create admin user if not exists
    async with async_session_maker() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(User).where(User.username == settings.ADMIN_USERNAME)
        )
        admin = result.scalar_one_or_none()
        
        if not admin:
            admin = User(
                username=settings.ADMIN_USERNAME,
                email=settings.ADMIN_EMAIL,
                hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
                role="admin",
                is_active=True
            )
            session.add(admin)
            await session.commit()
            print(f"Admin user created: {settings.ADMIN_USERNAME}")
