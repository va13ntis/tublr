import requests
from requests.exceptions import RequestException

BASE_URL = "http://localhost:8000"
TIMEOUT = 30


def test_user_registration_should_create_new_user_after_otp_verification():
    session = requests.Session()

    # Step 1: Get the registration page to retrieve the QR code for OTP setup and cookies
    try:
        reg_page_resp = session.get(f"{BASE_URL}/register", timeout=TIMEOUT)
        assert reg_page_resp.status_code == 200
        assert "text/html" in reg_page_resp.headers.get("Content-Type", ""), "Registration page content type is not HTML"
        # QR code presence check (heuristic): page content contains 'qr' or 'img' case insensitive
        page_text_lower = reg_page_resp.text.lower()
        assert "qr" in page_text_lower or "img" in page_text_lower, "QR code or image not found on registration page"
    except RequestException as e:
        assert False, f"Failed to get registration page: {e}"

    # Test failure: invalid OTP should return registration page with error
    invalid_otp_payload = {"otp": "000000"}

    try:
        resp = session.post(f"{BASE_URL}/register", data=invalid_otp_payload, timeout=TIMEOUT, allow_redirects=False)
        # On failure, response code 200 and registration page with error message expected as per PRD
        assert resp.status_code == 200, f"Expected status code 200 on invalid OTP, got {resp.status_code}"
        assert "text/html" in resp.headers.get("Content-Type", ""), "Response content type is not HTML on invalid OTP"
        # The page should contain an error message or registration form again
        assert "error" in resp.text.lower() or "register" in resp.text.lower(), "Error message or registration form not found on invalid OTP response"
    except RequestException as e:
        assert False, f"Registration with invalid OTP failed unexpectedly: {e}"

    # Test success: try registering with a valid OTP (hypothetical '123456')
    valid_otp_payload = {"otp": "123456"}

    try:
        resp = session.post(f"{BASE_URL}/register", data=valid_otp_payload, timeout=TIMEOUT, allow_redirects=False)
        # On success, server responds with 302 Redirect to home page
        assert resp.status_code == 302, f"Expected status code 302 on valid OTP, got {resp.status_code}"
        location = resp.headers.get("Location", "")
        assert location == "/", f"Redirect location is not home page: {location}"
    except RequestException as e:
        assert False, f"Registration with valid OTP failed unexpectedly: {e}"


test_user_registration_should_create_new_user_after_otp_verification()
