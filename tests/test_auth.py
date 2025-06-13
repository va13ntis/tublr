# tests/test_auth.py
import pyotp
import pytest
from fastapi import status
from starlette.middleware.sessions import SessionMiddleware
import re

def test_register_and_login_flow(client):
    # First set the username in a regular request
    response = client.post("/login", data={"username": "newuser"})
    assert response.status_code == status.HTTP_200_OK

    # Now try to register
    response = client.get("/register")
    assert response.status_code == status.HTTP_200_OK

def test_login_page(client):
    response = client.get("/login")
    assert response.status_code == status.HTTP_200_OK
    assert '<form method="post" action="/login"' in response.text

def test_login_success(client, test_user):
    response = client.post(
        "/login",
        data={"username": "testuser"},
        follow_redirects=True
    )
    assert response.status_code == status.HTTP_200_OK
    assert 'method="post"' in response.text
    assert 'action="/otp"' in response.text
    assert "Invalid OTP" not in response.text

def test_login_user_not_found(client):
    response = client.post(
        "/login",
        data={"username": "nonexistent"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert "User not found" in response.text

def test_otp_page(client, test_user):
    # First login to set session
    client.post("/login", data={"username": "testuser"}, follow_redirects=True)
    
    response = client.get("/otp")
    assert response.status_code == status.HTTP_200_OK
    assert 'method="post"' in response.text
    assert 'action="/otp"' in response.text

def test_verify_otp_success(client, test_user):
    # First login to set session
    response = client.post("/login", data={"username": "testuser"})
    assert response.status_code == status.HTTP_200_OK
    
    # Generate valid OTP
    totp = pyotp.TOTP(test_user.otp)
    valid_otp = totp.now()
    
    response = client.post(
        "/otp",
        data={"otp": valid_otp}
    )
    assert response.status_code == status.HTTP_200_OK
    assert "Invalid OTP" not in response.text

def test_verify_otp_invalid(client, test_user):
    # First login to set session
    client.post("/login", data={"username": "testuser"})
    
    response = client.post(
        "/otp",
        data={"otp": "invalid"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert "Invalid OTP" in response.text

def test_register_page(client):
    # First set username in session through login
    response = client.post("/login", data={"username": "newuser"})
    assert response.status_code == status.HTTP_200_OK
    
    response = client.get("/register")
    assert response.status_code == status.HTTP_200_OK
    assert '<form method="post" action="/register"' in response.text

def test_register_success(client):
    # First set username in session through login
    response = client.post("/login", data={"username": "newuser"})
    assert response.status_code == status.HTTP_200_OK
    
    # Get register page to set OTP secret
    response = client.get("/register")
    assert response.status_code == status.HTTP_200_OK
    
    # Extract OTP secret from the response
    match = re.search(r'id="otpSecret">([^<]+)', response.text)
    assert match is not None
    otp_secret = match.group(1)
    
    # Now try to register with a valid OTP
    totp = pyotp.TOTP(otp_secret)
    valid_otp = totp.now()
    
    response = client.post(
        "/register",
        data={"otp": valid_otp},
        follow_redirects=True
    )
    assert response.status_code == status.HTTP_200_OK
    assert "Invalid OTP" not in response.text

def test_register_invalid_otp(client):
    # First set username in session through login
    response = client.post("/login", data={"username": "newuser"})
    assert response.status_code == status.HTTP_200_OK
    
    # Get register page to set OTP secret
    response = client.get("/register")
    assert response.status_code == status.HTTP_200_OK
    
    response = client.post(
        "/register",
        data={"otp": "invalid"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert "Invalid OTP" in response.text

def test_ip_middleware_recognized_ip(client, recognized_ip):
    # Set user_id cookie
    client.cookies.set("user_id", str(recognized_ip.user_id))
    
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK

def test_ip_middleware_unrecognized_ip(client, test_user):
    # Set user_id cookie but with unrecognized IP
    client.cookies.set("user_id", str(test_user.id))
    
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    assert "/login" in response.url.path
