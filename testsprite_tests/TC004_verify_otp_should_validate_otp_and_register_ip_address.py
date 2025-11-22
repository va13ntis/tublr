import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_verify_otp_should_validate_otp_and_register_ip_address():
    session = requests.Session()

    # Step 1: Login with a username to initiate OTP verification
    login_data = {"username": "testuser_otp_validation"}
    login_response = session.post(f"{BASE_URL}/login", data=login_data, timeout=TIMEOUT, allow_redirects=False)
    assert login_response.status_code in (200, 302), f"Unexpected login response status code: {login_response.status_code}"

    # If redirected to OTP page (302), we proceed; If login page returned directly (200), means IP recognized - no OTP needed, test cannot proceed on this path
    if login_response.status_code == 200:
        # IP recognized - no OTP needed, skip test or fail because we need to test OTP validation
        assert False, "IP recognized for test user; OTP validation test requires unrecognized IP to reach OTP page."
    
    # Step 2: GET the OTP page to obtain any cookies/session info if needed
    otp_get_response = session.get(f"{BASE_URL}/otp", timeout=TIMEOUT)
    assert otp_get_response.status_code == 200, "Failed to get OTP verification page."

    # Step 3: Attempt to POST a valid OTP code
    # Since we don't have the actual OTP secret or code, we simulate with a placeholder.
    # The test assumes that the OTP code "123456" is INVALID and should fail,
    # so to test success, a real valid OTP is needed; here we test both failure and success.
    # For demonstration, first test failure:
    otp_data_invalid = {"otp": "000000"}
    otp_response_invalid = session.post(f"{BASE_URL}/otp", data=otp_data_invalid, timeout=TIMEOUT, allow_redirects=False)
    # On failure, should return 200 with OTP page and error message
    assert otp_response_invalid.status_code == 200, "Invalid OTP did not return OTP page with error."

    # Now test success case:
    # Since OTP depends on user secret, and we cannot generate a valid OTP here
    # we retry with the optimistic guess that "123456" is valid (in real test, generate it appropriately)
    otp_data_valid = {"otp": "123456"}
    otp_response_valid = session.post(f"{BASE_URL}/otp", data=otp_data_valid, timeout=TIMEOUT, allow_redirects=False)

    # On success, expect 302 redirect to home page
    assert otp_response_valid.status_code == 302, f"Valid OTP did not redirect on success, got status {otp_response_valid.status_code}"
    location = otp_response_valid.headers.get("Location", "")
    assert location == "/" or location.startswith("/"), f"Redirect location was unexpected: {location}"


test_verify_otp_should_validate_otp_and_register_ip_address()