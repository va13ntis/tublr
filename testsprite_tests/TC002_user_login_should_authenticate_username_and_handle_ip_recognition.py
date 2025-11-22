import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_user_login_authenticate_username_and_handle_ip_recognition():
    session = requests.Session()
    try:
        # Prepare valid username payload
        username = "testuser"
        payload = {"username": username}
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        response = session.post(f"{BASE_URL}/login", data=payload, headers=headers, timeout=TIMEOUT, allow_redirects=False)

        # Validate response status code for redirect (302) or bad login (200)
        assert response.status_code in (200, 302), f"Unexpected status code: {response.status_code}"
        
        if response.status_code == 302:
            # Check Location header for redirect target
            location = response.headers.get("Location", "")
            assert location in ["/", "/otp"], f"Unexpected redirect location: {location}"
            # If IP recognized redirect to home page
            if location == "/":
                # Successful login redirect to home page
                # Optionally, verify by following redirect
                home_resp = session.get(f"{BASE_URL}{location}", timeout=TIMEOUT)
                assert home_resp.status_code == 200, "Home page did not return 200 OK"
                assert "YouTube" in home_resp.text or "input" in home_resp.text.lower(), "Home page content unexpected"
            else:
                # Redirected to OTP verification page
                otp_resp = session.get(f"{BASE_URL}{location}", timeout=TIMEOUT)
                assert otp_resp.status_code == 200, "OTP page did not return 200 OK"
                assert "OTP" in otp_resp.text or "verification" in otp_resp.text.lower(), "OTP page content unexpected"
        else:
            # 200 response status means login page returned with error (e.g. bad username)
            assert "error" in response.text.lower() or "login" in response.text.lower(), "Login page should indicate error or show login form"
    finally:
        session.close()

test_user_login_authenticate_username_and_handle_ip_recognition()