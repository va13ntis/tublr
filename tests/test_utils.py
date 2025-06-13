import base64
import io
import pyotp
import qrcode
from app.main import generate_otp, image_to_str

def test_generate_otp():
    # Test that generated OTP secret is valid base32
    otp_secret = generate_otp()
    assert isinstance(otp_secret, str)
    assert len(otp_secret) > 0
    
    # Verify it can be used with pyotp
    totp = pyotp.TOTP(otp_secret)
    assert isinstance(totp.now(), str)
    assert len(totp.now()) == 6

def test_image_to_str():
    # Create a test QR code
    test_img = qrcode.make("test data")
    
    # Convert to base64 string
    img_str = image_to_str(test_img)
    
    # Verify it's a valid base64 string
    assert isinstance(img_str, str)
    
    # Verify it can be decoded back to bytes
    try:
        decoded = base64.b64decode(img_str)
        assert isinstance(decoded, bytes)
    except Exception:
        pytest.fail("Failed to decode base64 string") 