import base64
import io
from datetime import datetime

import pyotp
import qrcode
from fastapi import Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse

from sqlalchemy.orm import Session

from app.db import get_db, User
from app.shared import templates


async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "username": "username"})


async def login(
    request: Request,
    username: str = Form(...),
    db: Session = Depends(get_db),
):
    client_ip = request.client.host
    response = RedirectResponse(url="/", status_code=302)

    user = db.query(User).filter_by(username=username).first()

    if user:
        return RedirectResponse(url="/otp")
    else:
        # Create new user
        new_user = "" #User(username=username, otp=generate_otp())
        db.add(new_user)
        db.commit()
        user = new_user
        return templates.TemplateResponse("login.html", {"request": request, "message": f"User created. Use OTP: {user.otp}"})

    # Update or create recognized IP
    # user = db.query(User).filter_by(user_id=user.id, ip_address=client_ip).first()
    # if not recognized:
    #   db.add(User(user_id=user.id, ip_address=client_ip))
    # else:
    #    recognized.last_seen = datetime.utcnow()
    # db.commit()

    # response.set_cookie(key="user_id", value=str(user.id), httponly=True)
    # return response



async def register(request: Request, user_id: int, db: Session = Depends(get_db)):
    client_ip = request.client.host

    # Check if user_id already exists
    user = db.query(User).filter_by(id=user_id).first()

    if user and user.otp_secret:
        otp_secret = user.otp_secret
    else:
        # Generate new OTP secret
        otp_secret = pyotp.random_base32()
        if user:
            user.otp_secret = otp_secret
            db.commit()
        else:
            new_entry = User(user_id=user_id, ip_address=client_ip, otp_secret=otp_secret)
            db.add(new_entry)
            db.commit()

    # Create OTP URI
    otp_uri = pyotp.totp.TOTP(otp_secret).provisioning_uri(name=str(user_id), issuer_name="MyCoolApp")

    # Generate QR code
    img = qrcode.make(otp_uri)
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()

    html_content = f"""
    <html>
        <head><title>Register OTP</title></head>
        <body>
            <h1>Scan this QR Code with Google Authenticator</h1>
            <img src="data:image/png;base64,{img_str}" />
            <p>Or manually enter this code: <b>{otp_secret}</b></p>
        </body>
    </html>
    """

    return HTMLResponse(content=html_content)