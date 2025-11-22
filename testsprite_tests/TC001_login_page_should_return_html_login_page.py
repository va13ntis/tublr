import requests

def test_login_page_should_return_html_login_page():
    base_url = "http://localhost:8000"
    url = f"{base_url}/login"
    headers = {
        "Accept": "text/html"
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        assert False, f"Request to {url} failed: {e}"
    assert response.status_code == 200, f"Expected status code 200 but got {response.status_code}"
    content_type = response.headers.get("Content-Type", "")
    assert "text/html" in content_type, f"Expected 'text/html' in Content-Type header but got {content_type}"
    assert "<html" in response.text.lower() and "</html>" in response.text.lower(), "Response does not contain valid HTML"

test_login_page_should_return_html_login_page()