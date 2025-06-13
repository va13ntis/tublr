import pytest
from unittest.mock import Mock, patch
from fastapi import status
import io

MOCK_VIDEO_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

@pytest.fixture
def mock_youtube():
    with patch("app.main.YouTube") as mock:
        # Create mock stream objects
        mock_video_stream = Mock()
        mock_video_stream.resolution = "720p"
        mock_video_stream.video_codec = "vp9"
        mock_video_stream.is_progressive = True
        mock_video_stream.itag = 22
        mock_video_stream.includes_video_track = True
        mock_video_stream.title = "Test Video"
        mock_video_stream.stream_to_buffer = lambda buf: buf.write(b"test video data")
        mock_video_stream.filesize = 1024

        mock_audio_stream = Mock()
        mock_audio_stream.abr = "128kbps"
        mock_audio_stream.audio_codec = "opus"
        mock_audio_stream.itag = 140
        mock_audio_stream.includes_video_track = False
        mock_audio_stream.title = "Test Audio"
        mock_audio_stream.stream_to_buffer = lambda buf: buf.write(b"test audio data")
        mock_audio_stream.filesize = 512

        # Configure mock YouTube instance
        mock_instance = Mock()
        mock_instance.title = "Test Video"
        mock_instance.thumbnail_url = "https://example.com/thumbnail.jpg"
        mock_instance.streams = Mock()
        mock_instance.streams.filter.return_value = [mock_video_stream, mock_audio_stream]
        mock_instance.streams.get_by_itag.return_value = mock_video_stream
        mock_instance.streams.get_highest_resolution.return_value = mock_video_stream
        mock_instance.streams.get_audio_only.return_value = mock_audio_stream

        mock.return_value = mock_instance
        yield mock

def test_available_streams(client, mock_youtube, test_user, recognized_ip):
    # Set user_id cookie for authentication
    client.cookies.set("user_id", str(test_user.id))
    
    response = client.post(
        "/streams",
        data={"video_url": MOCK_VIDEO_URL}
    )
    assert response.status_code == status.HTTP_200_OK
    content = response.text
    assert "720p" in content
    assert "128kbps" in content

def test_download_by_itag(client, mock_youtube, test_user, recognized_ip):
    # Set user_id cookie for authentication
    client.cookies.set("user_id", str(test_user.id))
    
    response = client.get(f"/download?video_url={MOCK_VIDEO_URL}&itag=22")
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "video/mp4"
    assert "attachment" in response.headers["content-disposition"]
    assert b"test video data" == response.content

def test_download_video(client, mock_youtube, test_user, recognized_ip):
    # Set user_id cookie for authentication
    client.cookies.set("user_id", str(test_user.id))
    
    response = client.get(f"/download_video?video_url={MOCK_VIDEO_URL}")
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "video/mp4"
    assert "attachment" in response.headers["content-disposition"]
    assert b"test video data" == response.content

def test_download_audio(client, mock_youtube, test_user, recognized_ip):
    # Set user_id cookie for authentication
    client.cookies.set("user_id", str(test_user.id))
    
    response = client.get(f"/download_audio?video_url={MOCK_VIDEO_URL}")
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "audio/mp3"
    assert "attachment" in response.headers["content-disposition"]
    assert b"test audio data" == response.content

def test_invalid_video_url(client, mock_youtube, test_user, recognized_ip):
    # Set user_id cookie for authentication
    client.cookies.set("user_id", str(test_user.id))
    
    # Configure mock to raise an exception
    mock_youtube.side_effect = Exception("Invalid URL")
    
    response = client.post(
        "/streams",
        data={"video_url": "invalid_url"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert "Invalid URL" in response.text

def test_sanitize_filename():
    from app.main import sanitize_filename
    
    # Test various filename scenarios
    assert sanitize_filename("Test Video!") == "test-video"
    assert sanitize_filename("My Awesome Video 123") == "my-awesome-video-123"
    assert sanitize_filename("Special@#$Characters") == "specialcharacters"
    assert sanitize_filename("Unicode Тест") == "unicode-test" 