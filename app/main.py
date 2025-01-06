import io
import re

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pytubefix import YouTube

# Initialize FastAPI app
app = FastAPI()

# Initialize Jinja2 templates
templates = Jinja2Templates(directory="templates")


# Serve the HTML page
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# Get available video qualities
@app.get("/available_streams")
async def get_available_streams(video_url: str):
    try:
        yt = YouTube(video_url)
        video_streams = []
        audio_streams = []

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
        return JSONResponse({"error": str(e)}, status_code=400)


# Download by itag
@app.get("/download")
async def download(video_url: str, itag: int):
    try:
        yt = YouTube(video_url)
        stream = yt.streams.get_by_itag(itag)

        if not stream:
            raise HTTPException(status_code=404, detail="Stream not found.")

        buffer = io.BytesIO()
        stream.stream_to_buffer(buffer)
        buffer.seek(0)

        headers = {
            "Content-Disposition": f"attachment; filename={sanitize_filename(yt.title)}.{'mp4' if stream.includes_video_track else 'mp3'}"
        }

        return StreamingResponse(
            buffer,
            media_type="video/mp4" if stream.includes_video_track else "audio/mp3",
            headers=headers,
        )
    except Exception as e:
        return {"error": str(e)}


# Dovload video only
@app.get("/download_video")
async def download_video(video_url: str):
    try:
        yt = YouTube(video_url)
        stream = yt.streams.get_highest_resolution()

        return prepare_response(stream)

    except Exception as e:
        return {"error": str(e)}


# Download audio only
@app.get("/download_audio")
async def download_audio(video_url: str):
    try:
        yt = YouTube(video_url)
        stream = yt.streams.get_audio_only()

        return prepare_response(stream)

    except Exception as e:
        return {"error": str(e)}


# Prepare response
def prepare_response(stream):
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found.")

    buffer = io.BytesIO()
    stream.stream_to_buffer(buffer)
    buffer.seek(0)

    headers = {
        "Content-Disposition": f"attachment; filename={sanitize_filename(stream.title)}.{'mp4' if stream.includes_video_track else 'mp3'}"
    }

    return StreamingResponse(
        buffer,
        media_type="video/mp4" if stream.includes_video_track else "audio/mp3",
        headers=headers,
    )


# Sanitize filename using the improved expression
def sanitize_filename(filename):
    # This pattern allows letters, digits, spaces, and other specified characters
    return re.sub(r"[^A-Za-z0-9\s\-_~,;:\[\]\(\)\.]", "", filename)
