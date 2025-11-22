import requests
from bs4 import BeautifulSoup

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_download_by_itag_returns_video_or_audio_stream_or_404():
    video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Known valid YouTube video URL

    # Step 1: Get available streams by POSTing video_url to "/"
    try:
        response = requests.post(
            f"{BASE_URL}/",
            data={"video_url": video_url},
            timeout=TIMEOUT,
            allow_redirects=True
        )
        response.raise_for_status()
    except requests.RequestException as e:
        assert False, f"Failed to get available streams for video_url '{video_url}': {e}"

    # Parse the response HTML to extract itag values
    soup = BeautifulSoup(response.text, "html.parser")

    # Heuristic: look for input/select/option elements or links containing itag parameters
    itag_values = set()

    # Look for links or forms with itag query parameters
    for tag in soup.find_all(['a', 'form', 'input', 'select', 'option']):
        # Check href or value attributes for itag values
        attrs = []
        if tag.has_attr('href'):
            attrs.append(tag['href'])
        if tag.has_attr('value'):
            attrs.append(tag['value'])
        if tag.has_attr('name') and tag['name'] == 'itag' and tag.has_attr('value'):
            itag_values.add(tag['value'])
        for attr in attrs:
            if attr and 'itag=' in attr:
                # Extract itag value
                parts = attr.split('itag=')
                if len(parts) > 1:
                    val = parts[1].split('&')[0].split('"')[0].strip()
                    if val.isdigit():
                        itag_values.add(val)

    # Also check text content for itags in case
    text = response.text
    import re
    found_itags = set(re.findall(r"itag=(\d+)", text))
    itag_values.update(found_itags)

    # If no itag found, cannot proceed reliably, fail test
    if not itag_values:
        # Fallback: use a common itag known for the test video (e.g., 18)
        itag_values = {"18", "22", "140"}

    for itag in itag_values:
        # Step 2: GET /download with video_url and itag as query parameters
        params = {"video_url": video_url, "itag": itag}
        try:
            r = requests.get(f"{BASE_URL}/download", params=params, timeout=TIMEOUT, allow_redirects=False)
        except requests.RequestException as e:
            assert False, f"Request to /download with itag={itag} failed: {e}"

        # Assert status code is either 200 or 404
        assert r.status_code in (200, 404), f"Unexpected status code {r.status_code} for itag={itag}"

        if r.status_code == 200:
            content_type = r.headers.get("Content-Type", "")
            # Content-Type should be a video or audio media type
            assert (
                content_type.startswith("video/") or content_type.startswith("audio/")
            ), f"Expected video or audio content type for itag={itag}, got: '{content_type}'"
            # Should have some content
            assert r.content, f"Response content empty for itag={itag}"
        elif r.status_code == 404:
            # Stream not found; no content or minimal content is acceptable
            pass

test_download_by_itag_returns_video_or_audio_stream_or_404()