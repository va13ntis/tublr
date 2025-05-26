import base64
import io
import logging
import re
from datetime import datetime
from pathlib import Path

import pyotp
import qrcode
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Form, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pytubefix import YouTube
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware
from starlette.templating import Jinja2Templates

from app.db import get_db, RecognizedIP, User

FORMAT = '%(asctime)s %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI()

app.add_middleware(SessionMiddleware, secret_key="your-secret-key")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.middleware("http")
async def ip_check_middleware(request: Request, call_next):
    public_paths = ["/favicon.ico", "/login", "/otp", "/register", "/static"] #, "/available_streams", "/download", "/download_video", "/download_audio"]
    if any(request.url.path.startswith(path) for path in public_paths):
        return await call_next(request)

    db: Session = next(get_db())
    client_ip = request.client.host
    user_id = request.cookies.get("user_id")

    if user_id:
        ip_entry = db.query(RecognizedIP).filter_by(user_id=user_id, ip_address=client_ip).first()
        if ip_entry:
            ip_entry.last_seen = datetime.now()
            db.commit()
            return await call_next(request)

    # No recognized IP — redirect to login
    return RedirectResponse(url="/login")


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        user = db.query(User).filter_by(username=username).first()

        if user:
            request.session["user_id"] = user.id
            request.session["totp_secret"] = user.otp

            return RedirectResponse("/otp", status_code=302)

        request.session["username"] = username

        return templates.TemplateResponse("login.html", {"request": request, "username": username, "user_not_found": "true"})
    except Exception as e:
        logger.error(e)
        return templates.TemplateResponse("login.html", {"request": request, "error": e})


@app.get("/otp", response_class=HTMLResponse)
async def otp_page(request: Request):
    return templates.TemplateResponse("otp.html", {"request": request})


@app.post("/otp")
async def verify_otp(
    request: Request,
    otp: str = Form(...),
    db: Session = Depends(get_db)
):
    user_id = request.session["user_id"]
    totp_secret = request.session["totp_secret"]
    client_ip = request.client.host
    response = RedirectResponse(url="/", status_code=302)

    if not pyotp.TOTP(totp_secret).verify(otp):
        return templates.TemplateResponse("otp.html", {"request": request, "error": "Invalid OTP"})

    # Update or create recognized IP
    recognized = db.query(RecognizedIP).filter_by(user_id=user_id, ip_address=client_ip).first()

    if not recognized:
        db.add(RecognizedIP(user_id=user_id, ip_address=client_ip))
    else:
        recognized.last_seen = datetime.now()
    db.commit()

    response.set_cookie(key="user_id", value=str(user_id), httponly=True)
    return response


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    username = request.session["username"]
    otp_secret = generate_otp()
    otp_uri = pyotp.totp.TOTP(otp_secret).provisioning_uri(name=username, issuer_name="Tublr")
    img_str = image_to_str(qrcode.make(otp_uri))

    request.session["otp_secret"] = otp_secret

    return templates.TemplateResponse("register.html", {"request": request, "otp_secret": otp_secret, "img_str": img_str})


@app.post("/register")
async def register(
        request: Request,
        otp: str = Form(...),
        db: Session = Depends(get_db)
):
    username = request.session["username"]
    otp_secret = request.session["otp_secret"]

    if not pyotp.TOTP(otp_secret).verify(otp):
        return templates.TemplateResponse("register.html", {"request": request, "error": "Invalid OTP"})

    # Create new user
    user = User(username=username, otp=otp_secret)
    db.add(user)
    db.commit()

    client_ip = request.client.host
    response = RedirectResponse(url="/", status_code=302)

    # Update or create recognized IP
    recognized = db.query(RecognizedIP).filter_by(user_id=user.id, ip_address=client_ip).first()
    if not recognized:
        db.add(RecognizedIP(user_id=user.id, ip_address=client_ip))
    else:
        recognized.last_seen = datetime.now()
    db.commit()

    response.set_cookie(key="user_id", value=str(user.id), httponly=True)
    return response


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/")
async def available_streams(request: Request, video_url: str = Form(...)):
    context = {"request": request, "video_url": video_url}

    try:
        logger.info(f"Trying to get available streams from {video_url}")

        yt = YouTube(video_url)
        video_streams = []
        audio_streams = []

        logger.info(f"Found {len(yt.streams)} streams")

        # Filter video streams
        for stream in yt.streams.filter(type="video"):
            if stream.resolution is None:
                continue

            video_streams.append(
                {
                    "resolution": stream.resolution or "N/A",
                    "video_codec": stream.video_codec or "N/A",
                    "includes_audio": stream.is_progressive,  # True if includes audio
                    "itag": stream.itag,
                }
            )

        # Filter audio streams
        for stream in yt.streams.filter(type="audio"):
            audio_streams.append(
                {
                    "bitrate": stream.abr or "N/A",
                    "audio_codec": stream.audio_codec or "N/A",
                    "itag": stream.itag,
                }
            )

        # Sort video streams by resolution descending
        video_streams = sorted(
            video_streams,
            key=lambda x: (
                int(x["resolution"].replace("p", "")) if x["resolution"] != "N/A" else 0
            ),
            reverse=True,
        )

        # Sort audio streams by bitrate descending
        audio_streams = sorted(
            audio_streams,
            key=lambda x: (
                int(x["bitrate"].replace("kbps", "")) if x["bitrate"] != "N/A" else 0
            ),
            reverse=True,
        )

        context.update({
            "thumbnail_url": yt.thumbnail_url,
            "video_streams": video_streams,
            "audio_streams": audio_streams,
        })

    except Exception as e:
        logger.error(e)
        context["error"] = str(e)

    return templates.TemplateResponse("index.html", context)


# Download by itag
@app.get("/download")
async def download(video_url: str, itag: int):
    try:
        yt = YouTube(video_url)
        stream = yt.streams.get_by_itag(itag)

        return prepare_response(stream)

    except Exception as e:
        logger.error(e)
        return {"error": str(e)}


# Download video only
@app.get("/download_video")
async def download_video(video_url: str):
    try:
        yt = YouTube(video_url)
        stream = yt.streams.get_highest_resolution()

        return prepare_response(stream)

    except Exception as e:
        logger.error(e)
        return {"error": str(e)}


# Download audio only
@app.get("/download_audio")
async def download_audio(video_url: str):
    try:
        yt = YouTube(video_url)
        stream = yt.streams.get_audio_only()

        return prepare_response(stream)

    except Exception as e:
        logger.error(e)
        return {"error": str(e)}


# Prepare response
def prepare_response(stream):
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found.")

    buffer = io.BytesIO()
    stream.stream_to_buffer(buffer)
    buffer.seek(0)

    headers = {
        "Content-Disposition":
        f"attachment; filename={sanitize_filename(stream.title)}.{'mp4' if stream.includes_video_track else 'mp3'}"
    }

    return StreamingResponse(
        buffer,
        media_type="video/mp4" if stream.includes_video_track else "audio/mp3",
        headers=headers,
    )


# Sanitize filename using the improved expression
def sanitize_filename(filename):
    # This pattern allows letters, digits, spaces, and other specified characters
    return re.sub(r"[^A-Za-z0-9\s\-_~,;:\[\]().]", "", filename)


def generate_otp():
    return pyotp.random_base32()


def image_to_str(img):
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()


if __name__=="__main__":
    uvicorn.run("main:app",
                host="0.0.0.0",
                port=8000,
                reload=True,
                log_level="debug",
                workers=1)