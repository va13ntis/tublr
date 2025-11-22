import requests

def test_home_page_should_return_html_home_page():
    base_url = "http://localhost:8000"
    url = f"{base_url}/"
    headers = {
        "Accept": "text/html"
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        # Assert status code 200
        assert response.status_code == 200, f"Expected status code 200 but got {response.status_code}"
        # Assert Content-Type header indicates HTML content
        content_type = response.headers.get("Content-Type", "")
        assert "text/html" in content_type, f"Expected 'text/html' in Content-Type but got '{content_type}'"
        # Assert response content is not empty
        assert response.text.strip() != "", "Expected non-empty HTML content on home page"
    except requests.RequestException as e:
        assert False, f"HTTP request failed: {e}"

test_home_page_should_return_html_home_page()