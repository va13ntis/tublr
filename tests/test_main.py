import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_homepage():
    """Test if the homepage loads correctly."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"YouTube downloader" in response.content
