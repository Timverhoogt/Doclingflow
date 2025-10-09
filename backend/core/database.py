"""
PostgreSQL database connection and session management.
"""

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from backend.core.config import get_settings


# Create base class for declarative models
Base = declarative_base()


class DatabaseManager:
    """Manages database connections and sessions."""

    def __init__(self):
        self.settings = get_settings()
        self.engine = None
        self.SessionLocal = None
        self._initialize_engine()

    def _initialize_engine(self):
        """Initialize SQLAlchemy engine and session factory."""
        database_url = self.settings.database.database_url

        # Create engine with connection pooling
        self.engine = create_engine(
            database_url,
            pool_pre_ping=True,  # Verify connections before using
            pool_size=5,
            max_overflow=10,
            echo=self.settings.debug,  # Log SQL queries in debug mode
        )

        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

    def create_tables(self):
        """Create all database tables."""
        Base.metadata.create_all(bind=self.engine)

    def drop_tables(self):
        """Drop all database tables. Use with caution!"""
        Base.metadata.drop_all(bind=self.engine)

    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()

    def close(self):
        """Close database engine."""
        if self.engine:
            self.engine.dispose()


# Global database manager instance
_db_manager: DatabaseManager | None = None


def get_db_manager() -> DatabaseManager:
    """Get global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function for FastAPI to get database sessions.

    Usage in FastAPI routes:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db_manager = get_db_manager()
    db = db_manager.get_session()
    try:
        yield db
    finally:
        db.close()


def init_database():
    """Initialize database (create tables if they don't exist)."""
    db_manager = get_db_manager()
    db_manager.create_tables()


def close_database():
    """Close database connections."""
    global _db_manager
    if _db_manager is not None:
        _db_manager.close()
        _db_manager = None
