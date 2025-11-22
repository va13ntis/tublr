import requests

def test_registration_page_returns_html_with_qr_code():
    base_url = "http://localhost:8000"
    url = f"{base_url}/register"
    headers = {
        "Accept": "text/html"
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        content_type = response.headers.get("Content-Type", "")
        assert "text/html" in content_type, f"Expected Content-Type to include 'text/html', got {content_type}"
        html_content = response.text
        assert "qr" in html_content.lower() or "qrcode" in html_content.lower(), "QR code not found in registration page HTML content"
    except requests.RequestException as e:
        assert False, f"Request failed: {e}"

test_registration_page_returns_html_with_qr_code()