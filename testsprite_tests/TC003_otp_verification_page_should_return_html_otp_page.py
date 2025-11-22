import requests

def test_otp_verification_page_returns_html():
    base_url = "http://localhost:8000"
    url = f"{base_url}/otp"
    headers = {
        "Accept": "text/html"
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        assert response.status_code == 200, f"Expected status code 200 but got {response.status_code}"
        content_type = response.headers.get("Content-Type", "")
        assert "text/html" in content_type, f"Expected 'text/html' in Content-Type but got '{content_type}'"
        assert "<html" in response.text.lower(), "Response body does not contain expected HTML content."
    except requests.RequestException as e:
        assert False, f"Request to /otp failed: {e}"

test_otp_verification_page_returns_html()