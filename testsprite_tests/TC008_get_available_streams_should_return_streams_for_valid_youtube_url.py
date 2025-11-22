import requests

def test_get_available_streams_should_return_streams_for_valid_youtube_url():
    base_url = "http://localhost:8000"
    endpoint = f"{base_url}/"
    video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "video_url": video_url
    }
    try:
        response = requests.post(endpoint, headers=headers, data=data, timeout=30)
        # Validate a successful response
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        content_type = response.headers.get("Content-Type", "")
        assert "text/html" in content_type, f"Expected 'text/html' content type but got: {content_type}"
        html_content = response.text
        # Check presence of video URL in response HTML to ensure video info is included
        assert video_url in html_content, "Response HTML does not contain the submitted video URL"
        # Check presence of indicative keywords for stream listings
        assert ("video" in html_content.lower() or "audio" in html_content.lower()), "Response HTML does not contain video or audio streams listing"
    except requests.RequestException as e:
        assert False, f"Request failed with exception: {e}"

test_get_available_streams_should_return_streams_for_valid_youtube_url()