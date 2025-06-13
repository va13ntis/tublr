from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base

# Use SQLite in-memory database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"

def get_test_engine():
    """Create a thread-safe SQLite engine for testing."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    Base.metadata.create_all(engine)
    return engine

def get_test_session():
    """Get a test database session."""
    engine = get_test_engine()
    TestingSessionLocal = sessionmaker(bind=engine)
    return TestingSessionLocal() 