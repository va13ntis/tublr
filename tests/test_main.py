import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture
def video_url():
    """Provide a sample YouTube video URL for testing."""
    return "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Replace with a valid video URL

def test_homepage():
    """Test if the homepage loads correctly."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"YouTube downloader" in response.content

def test_get_available_streams(video_url):
    """Test the video details fetch endpoint."""
    response = client.get("/available_streams?url={video_url}")
    assert response.status_code == 200
    data = response.json()
    assert "title" in data
    assert "streams" in data
    assert len(data["streams"]) > 0

def test_download_video(video_url):
    """Test the video download endpoint."""
    # Fetch video details to get a valid ITAG
    response = client.get("/available_streams?url={video_url}")
    video_data = response.json()
    itag = video_data["streams"][0]["itag"]  # Select the first available stream
    
    # Test the download endpoint
    download_response = client.get(f"/download?url={video_url}&itag={itag}", stream=True)
    assert download_response.status_code == 200
    assert download_response.headers["content-type"] == "video/mp4"

def test_invalid_video_url():
    """Test the behavior for invalid video URLs."""
    invalid_url = "https://www.youtube.com/watch?v=invalid"
    response = client.get("/available_streams?url={video_url}")
    assert response.status_code == 400
    assert "error" in response.json()

def test_audio_download(video_url):
    """Test audio-only download functionality."""
    # Fetch video details to get a valid ITAG for audio
    response = client.get("/available_streams?url={video_url}")
    video_data = response.json()
    audio_stream = next((s for s in video_data["streams"] if s["mime_type"].startswith("audio/")), None)
    assert audio_stream is not None

    # Test the download endpoint for audio
    itag = audio_stream["itag"]
    download_response = client.get(f"/download?url={video_url}&itag={itag}", stream=True)
    assert download_response.status_code == 200
    assert download_response.headers["content-type"] == "audio/mp4"

