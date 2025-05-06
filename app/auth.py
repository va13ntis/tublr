import base64
import io
from datetime import datetime

import pyotp
import qrcode
from fastapi import Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db, User, RecognizedIP
from app.shared import templates


async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


async def login(
    request: Request,
    username: str = Form(...),
    otp: str = Form(...),
    db: Session = Depends(get_db)
):
    client_ip = request.client.host
    response = RedirectResponse(url="/", status_code=302)

    user = db.query(User).filter_by(username=username).first()

    if user:
        if not pyotp.TOTP(user.otp).verify(otp):
            return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid OTP"})
    else:
        # Create new user
        new_user = User(username=username, otp=generate_otp())
        db.add(new_user)
        db.commit()
        user = new_user
        return HTMLResponse(generate_otp_qr(user))

    # Update or create recognized IP
    recognized = db.query(RecognizedIP).filter_by(user_id=user.id, ip_address=client_ip).first()
    if not recognized:
        db.add(RecognizedIP(user_id=user.id, ip_address=client_ip))
    else:
        recognized.last_seen = datetime.now()
    db.commit()

    response.set_cookie(key="user_id", value=str(user.id), httponly=True)
    return response


def generate_otp():
    return pyotp.random_base32()


def generate_otp_qr(user: User):
    otp_secret = user.otp

    # Create OTP URI
    otp_uri = pyotp.totp.TOTP(otp_secret).provisioning_uri(name=user.username, issuer_name="Tublr")

    # Generate QR code
    img_str = image_to_str(qrcode.make(otp_uri))

    return f"""
    <html>
        <head><title>Register OTP</title></head>
        <body>
            <h1>Scan this QR Code with Google Authenticator</h1>
            <img src="data:image/png;base64,{img_str}" />
            <p>Or manually enter this code: <b>{otp_secret}</b></p>
        </body>
    </html>
    """

def image_to_str(img):
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()