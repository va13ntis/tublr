import io
import logging
import re
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, RedirectResponse
from pytubefix import YouTube
from sqlalchemy.orm import Session

from app.auth import login_page, login
from app.db import get_db, User
from app.shared import templates

FORMAT = '%(asctime)s %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()


@app.middleware("http")
async def ip_check_middleware(request: Request, call_next):
    public_paths = ["/login", "/static", "/available_streams", "/download", "/download_video", "/download_audio"]
    if any(request.url.path.startswith(path) for path in public_paths):
        return await call_next(request)

    db: Session = next(get_db())
    client_ip = request.client.host
    user_id = request.cookies.get("user_id")

    if user_id:
        ip_entry = db.query(User).filter_by(user_id=user_id, ip_address=client_ip).first()
        if ip_entry:
            ip_entry.last_seen = datetime.utcnow()
            db.commit()
            return await call_next(request)

    # No recognized IP — redirect to login
    return RedirectResponse(url="/login")


@app.get("/login", response_class=HTMLResponse)(login_page)
@app.post("/login")(login)
# @app.get("/register", response_class=HTMLResponse)(register)


# Serve the HTML page
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# Get available video qualities
@app.get("/available_streams")
async def get_available_streams(video_url: str):
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

        return JSONResponse(
            {
                "thumbnail_url": yt.thumbnail_url,
                "video_streams": video_streams,
                "audio_streams": audio_streams,
            }
        )

    except Exception as e:
        logger.error(e)
        return JSONResponse({"error": str(e)}, status_code=400)


# Download by itag
@app.get("/download")
async def download(video_url: str, itag: int):
    try:
        yt = YouTube(video_url)
        stream = yt.streams.get_by_itag(itag)

        prepare_response(stream)
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