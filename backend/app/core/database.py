import asyncio
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager

from app.core.config import settings

# Database engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=settings.DEBUG
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


@asynccontextmanager
async def get_db_session():
    """Get database session context manager."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def create_tables():
    """Create database tables."""
    # Import models to register them
    from app.models import database
    
    # Create tables
    Base.metadata.create_all(bind=engine)


async def check_db_connection() -> bool:
    """Check database connection health."""
    try:
        async with get_db_session() as db:
            db.execute("SELECT 1")
            return True
    except Exception:
        return False
