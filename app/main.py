import asyncio
import base64
import io
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import pyotp
import qrcode
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pytubefix import YouTube
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask
from starlette.middleware.sessions import SessionMiddleware
from starlette.templating import Jinja2Templates

from app import downloads
from app.db import get_db, RecognizedIP, User

FORMAT = '%(asctime)s %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent

DEV_MODE = os.getenv("TUBLR_DEV", "").lower() in ("1", "true", "yes")
if DEV_MODE:
    logger.warning("TUBLR_DEV is set: authentication is disabled")


async def cleanup_loop():
    while True:
        await asyncio.sleep(300)
        downloads.cleanup_expired()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    downloads.reset_download_dir()
    if not downloads.ffmpeg_available():
        logger.warning(f"ffmpeg not found ('{downloads.FFMPEG}'): video downloads that need merging with audio will fail")
    task = asyncio.create_task(cleanup_loop())
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan)

app.add_middleware(SessionMiddleware, secret_key="your-secret-key")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.middleware("http")
async def ip_check_middleware(request: Request, call_next):
    public_paths = ["/favicon.ico", "/login", "/otp", "/register", "/static"] #, "/available_streams", "/download", "/download_video", "/download_audio"]
    if DEV_MODE or any(request.url.path.startswith(path) for path in public_paths):
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
    return templates.TemplateResponse(request, "login.html", {"request": request})


@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        user = db.query(User).filter_by(username=username).first()

        if user:
            client_ip = request.client.host
            # Check if IP is already recognized for this user
            recognized_ip = db.query(RecognizedIP).filter_by(user_id=user.id, ip_address=client_ip).first()
            
            if recognized_ip:
                # IP is recognized (trusted device/location) - skip OTP verification
                # This is by design: users from previously verified IPs don't need to re-verify
                # OTP is only required for new/unrecognized IP addresses
                recognized_ip.last_seen = datetime.now()
                db.commit()
                response = RedirectResponse(url="/", status_code=302)
                response.set_cookie(key="user_id", value=str(user.id), httponly=True)
                return response
            else:
                # IP is not recognized - require OTP verification for security
                request.session["user_id"] = user.id
                request.session["totp_secret"] = user.otp
                return RedirectResponse("/otp", status_code=302)

        request.session["username"] = username

        return templates.TemplateResponse(request, "login.html", {"request": request, "username": username, "user_not_found": "true"})
    except Exception as e:
        logger.error(e)
        return templates.TemplateResponse(request, "login.html", {"request": request, "error": e})


@app.get("/otp", response_class=HTMLResponse)
async def otp_page(request: Request):
    return templates.TemplateResponse(request, "otp.html", {"request": request})


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
        return templates.TemplateResponse(request, "otp.html", {"request": request, "error": "Invalid OTP"})

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
    username = request.session.get("username")
    if not username:
        return RedirectResponse("/login", status_code=302)
    otp_secret = generate_otp()
    otp_uri = pyotp.totp.TOTP(otp_secret).provisioning_uri(name=username, issuer_name="Tublr")
    img_str = image_to_str(qrcode.make(otp_uri))

    request.session["otp_secret"] = otp_secret

    return templates.TemplateResponse(request, "register.html", {"request": request, "otp_secret": otp_secret, "img_str": img_str})


@app.post("/register")
async def register(
        request: Request,
        otp: str = Form(...),
        db: Session = Depends(get_db)
):
    username = request.session["username"]
    otp_secret = request.session["otp_secret"]

    if not pyotp.TOTP(otp_secret).verify(otp):
        return templates.TemplateResponse(request, "register.html", {"request": request, "error": "Invalid OTP"})

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
    return templates.TemplateResponse(request, "index.html", {"request": request})


@app.post("/")
async def available_streams(request: Request, video_url: str = Form(...)):
    context = {"request": request, "video_url": video_url}

    def load_options():
        yt = YouTube(video_url)
        return {
            "thumbnail_url": yt.thumbnail_url,
            "title": yt.title,
            "video_options": downloads.video_options(yt),
            "audio_options": downloads.audio_options(yt),
        }

    try:
        logger.info(f"Trying to get available streams from {video_url}")
        context.update(await asyncio.to_thread(load_options))
    except Exception as e:
        logger.error(e)
        context["error"] = str(e)

    return templates.TemplateResponse(request, "index.html", context)


def current_user_id(request: Request) -> str:
    user_id = request.cookies.get("user_id")
    if user_id:
        return user_id
    if DEV_MODE:
        return "dev"
    raise HTTPException(status_code=401, detail="Not logged in.")


@app.post("/jobs")
async def create_job(
    request: Request,
    video_url: str = Form(...),
    kind: str = Form(...),
    itag: int = Form(...),
):
    if kind not in ("video", "audio"):
        raise HTTPException(status_code=400, detail="kind must be 'video' or 'audio'.")
    job = downloads.create_job(current_user_id(request), kind, video_url, itag)
    return job.to_dict()


@app.get("/jobs/{job_id}")
async def job_status(request: Request, job_id: str):
    job = downloads.get_job(job_id, current_user_id(request))
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job.to_dict()


@app.get("/jobs/{job_id}/file")
async def job_file(request: Request, job_id: str):
    job = downloads.get_job(job_id, current_user_id(request))
    if not job or job.status != "ready" or not job.file_path or not job.file_path.exists():
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(
        job.file_path,
        filename=job.filename,
        media_type=job.media_type,
        background=BackgroundTask(downloads.remove_job, job),
    )


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