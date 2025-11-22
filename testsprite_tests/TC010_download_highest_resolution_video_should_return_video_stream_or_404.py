import requests

BASE_URL = "http://localhost:8000"
DOWNLOAD_VIDEO_ENDPOINT = f"{BASE_URL}/download_video"
GET_STREAMS_ENDPOINT = BASE_URL

def test_download_highest_resolution_video_should_return_video_stream_or_404():
    video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Example valid YouTube video URL

    # First, check if the video_url returns available streams by sending POST request to /
    try:
        streams_response = requests.post(
            GET_STREAMS_ENDPOINT,
            data={"video_url": video_url},
            timeout=30
        )
        assert streams_response.status_code == 200, f"Fetching streams failed with status {streams_response.status_code}"
    except (requests.RequestException, AssertionError) as e:
        raise AssertionError(f"Failed to fetch available streams for video_url: {e}")

    # Attempt to download highest resolution video stream
    try:
        download_response = requests.get(
            DOWNLOAD_VIDEO_ENDPOINT,
            params={"video_url": video_url},
            timeout=30,
            stream=True
        )
    except requests.RequestException as e:
        raise AssertionError(f"HTTP request to download highest resolution video failed: {e}")

    assert download_response.status_code in (200, 404), f"Expected status 200 or 404 but got {download_response.status_code}"

    if download_response.status_code == 200:
        content_type = download_response.headers.get("Content-Type", "")
        assert content_type.startswith("video/"), f"Expected video content-type but got {content_type}"
        # Optionally check if content-length is present and > 0
        content_length = download_response.headers.get("Content-Length")
        if content_length is not None:
            assert int(content_length) > 0, "Content-Length header is zero or invalid for video stream"
        # Read a few bytes to confirm stream is non-empty (without downloading all)
        try:
            chunk = next(download_response.iter_content(chunk_size=1024))
            assert chunk, "Video stream content is empty"
        except StopIteration:
            raise AssertionError("Video stream content is empty")
    else:
        # 404 Not Found means no video stream found; this is acceptable
        pass

test_download_highest_resolution_video_should_return_video_stream_or_404()