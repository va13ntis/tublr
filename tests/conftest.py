# tests/conftest.py
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import pyotp
from starlette.middleware.sessions import SessionMiddleware
from starlette.staticfiles import StaticFiles
from pathlib import Path

from app.db import Base, User
from app.main import app as main_app, get_db, BASE_DIR

@pytest.fixture(scope="session")
def engine():
    """Create a thread-safe SQLite engine for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)

@pytest.fixture
def db_session(engine) -> Session:
    """Creates a new database session for each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()
    
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()

def create_test_app():
    """Create a fresh FastAPI application for testing."""
    app = FastAPI()
    
    # Copy dependencies and middleware from main app
    app.dependency_overrides = main_app.dependency_overrides.copy()
    app.user_middleware = main_app.user_middleware.copy()
    
    # Add session middleware
    app.add_middleware(
        SessionMiddleware,
        secret_key="test_secret_key",
        session_cookie="session",
        max_age=3600,
        same_site="lax",
        https_only=False
    )
    
    # Mount static files
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
    
    # Copy all routes
    app.routes = main_app.routes.copy()
    
    return app

@pytest.fixture
def client(db_session):
    """Create a test client with a fresh database session."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app = create_test_app()
    app.dependency_overrides = {}
    app.dependency_overrides["get_db"] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
def authenticated_client(client, db_session):
    """Create a test client that's already authenticated."""
    # Create test user with valid OTP secret
    otp_secret = pyotp.random_base32()
    user = User(username="testuser", otp=otp_secret)
    db_session.add(user)
    db_session.commit()
    
    # Login
    response = client.post("/login", data={"username": "testuser"})
    assert response.status_code == 302
    
    # Get OTP code and verify
    totp = pyotp.TOTP(otp_secret)
    otp_code = totp.now()
    response = client.post("/otp", data={"otp": otp_code})
    assert response.status_code == 302
    
    return client

@pytest.fixture
def test_user(db_session):
    """Creates a test user for authentication tests."""
    user = User(
        username="testuser",
        otp="TESTSECRET123"
    )
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def test_recognized_ip(db_session, test_user):
    """Creates a test recognized IP for the test user."""
    from app.db import RecognizedIP
    ip = RecognizedIP(
        user_id=test_user.id,
        ip_address="127.0.0.1"
    )
    db_session.add(ip)
    db_session.commit()
    return ip
