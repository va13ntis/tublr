import pytest
from httpx import AsyncClient
from app.main import app  # Import your FastAPI app

@pytest.mark.asyncio
async def test_read_root():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}  # Adjust based on your app's response

@pytest.mark.asyncio
async def test_video_details():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/video?id=sample_video_id")
    assert response.status_code == 200
    assert "itag" in response.json()[0]  # Adjust based on your response structure

@pytest.mark.asyncio
async def test_invalid_video_id():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/video?id=invalid_id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Video not found"

def test_mock_video_details(mocker):
    mock_get_video = mocker.patch("pytubefix.YouTube.streams", return_value=[])
    response = app.get_video_details("mock_id")
    assert mock_get_video.called
    assert response == []
