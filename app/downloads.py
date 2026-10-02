from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import pytubefix.request
from pytubefix import YouTube

logger = logging.getLogger(__name__)

# pytubefix reports progress once per range request (9 MB by default), which is too coarse for a progress bar.
pytubefix.request.default_range_size = 1024 * 1024

DOWNLOAD_DIR = Path(os.getenv("TUBLR_DOWNLOAD_DIR") or Path(__file__).resolve().parent.parent / "downloads")
FFMPEG = os.getenv("TUBLR_FFMPEG") or "ffmpeg"
MAX_HEIGHT = int(os.getenv("TUBLR_MAX_HEIGHT") or 1080)
# Jobs share the Pi's CPU, disk and bandwidth, so they run one at a time by default.
MAX_JOBS = int(os.getenv("TUBLR_MAX_JOBS") or 1)
# Finished files that were never fetched (e.g. the tab was closed) are removed after this many seconds.
JOB_TTL = int(os.getenv("TUBLR_JOB_TTL") or 1800)

_executor = ThreadPoolExecutor(max_workers=MAX_JOBS)
_jobs: dict[str, "Job"] = {}
_lock = threading.Lock()


@dataclass
class Job:
    id: str
    user_id: str
    kind: str
    video_url: str
    itag: int
    status: str = "queued"
    progress: float = 0.0
    error: str | None = None
    file_path: Path | None = None
    filename: str | None = None
    media_type: str | None = None
    updated_at: float = field(default_factory=time.time)

    @property
    def work_dir(self) -> Path:
        return DOWNLOAD_DIR / safe_path_part(self.user_id) / self.id

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "status": self.status,
            "progress": round(self.progress, 1),
            "error": self.error,
        }


def safe_path_part(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", value) or "_"


def clean_title(title: str) -> str:
    value = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "", str(title)).strip(" .")
    return value[:150] or "download"


def ffmpeg_available() -> bool:
    return shutil.which(FFMPEG) is not None


def stream_height(stream) -> int:
    return int(stream.resolution.rstrip("p")) if stream.resolution else 0


def video_options(yt: YouTube) -> list[dict]:
    """One stream per resolution up to MAX_HEIGHT, preferring H.264 MP4 since it can be merged
    with AAC audio by stream copy and plays almost everywhere."""

    def rank(stream):
        return (stream.is_adaptive, (stream.video_codec or "").startswith("avc1"))

    best: dict[int, object] = {}
    for stream in yt.streams.filter(type="video", file_extension="mp4"):
        height = stream_height(stream)
        if not height or height > MAX_HEIGHT:
            continue
        if height not in best or rank(stream) > rank(best[height]):
            best[height] = stream

    return [
        {
            "itag": stream.itag,
            "label": f"{height}p{stream.fps if stream.fps and stream.fps > 30 else ''} · {(stream.video_codec or 'N/A').split('.')[0]}",
        }
        for height, stream in sorted(best.items(), reverse=True)
    ]


def audio_options(yt: YouTube) -> list[dict]:
    streams = sorted(
        yt.streams.filter(only_audio=True),
        key=lambda s: int((s.abr or "0kbps").replace("kbps", "")),
        reverse=True,
    )
    return [
        {
            "itag": stream.itag,
            "label": f"{stream.abr or 'N/A'} · {(stream.audio_codec or 'N/A').split('.')[0]} ({audio_extension(stream)})",
        }
        for stream in streams
    ]


def audio_extension(stream) -> str:
    return "m4a" if stream.subtype == "mp4" else stream.subtype


def create_job(user_id: str, kind: str, video_url: str, itag: int) -> Job:
    cleanup_expired()
    job = Job(id=uuid.uuid4().hex, user_id=user_id, kind=kind, video_url=video_url, itag=itag)
    with _lock:
        _jobs[job.id] = job
    _executor.submit(_run, job)
    return job


def get_job(job_id: str, user_id: str) -> Job | None:
    job = _jobs.get(job_id)
    return job if job and job.user_id == user_id else None


def remove_job(job: Job) -> None:
    with _lock:
        _jobs.pop(job.id, None)
    _remove_files(job)


def _remove_files(job: Job) -> None:
    shutil.rmtree(job.work_dir, ignore_errors=True)
    try:
        job.work_dir.parent.rmdir()
    except OSError:
        pass


def cleanup_expired() -> None:
    now = time.time()
    expired = [j for j in list(_jobs.values()) if j.status in ("ready", "error") and now - j.updated_at > JOB_TTL]
    for job in expired:
        logger.info(f"Removing expired job {job.id}")
        remove_job(job)


def reset_download_dir() -> None:
    """Files from a previous run can never be fetched, since jobs live in memory."""
    shutil.rmtree(DOWNLOAD_DIR, ignore_errors=True)
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _set(job: Job, **changes) -> None:
    for key, value in changes.items():
        setattr(job, key, value)
    job.updated_at = time.time()


def _run(job: Job) -> None:
    try:
        job.work_dir.mkdir(parents=True, exist_ok=True)
        if job.kind == "video":
            _download_video(job)
        else:
            _download_audio(job)
        _set(job, status="ready", progress=100)
    except Exception as e:
        logger.exception(f"Job {job.id} failed")
        _remove_files(job)
        _set(job, status="error", error=str(e) or e.__class__.__name__)


def _progress_tracker(job: Job, total_bytes: int, done_before: list[int]):
    def on_progress(stream, _chunk, bytes_remaining):
        done = done_before[0] + stream.filesize - bytes_remaining
        _set(job, progress=min(99.0, done * 100 / max(total_bytes, 1)))

    return on_progress


def _download_video(job: Job) -> None:
    done_before = [0]
    yt = YouTube(job.video_url)
    video = yt.streams.get_by_itag(job.itag)
    if not video or not video.includes_video_track or stream_height(video) > MAX_HEIGHT:
        raise ValueError("Selected video format is not available.")

    audio = None
    if not video.is_progressive:
        if not ffmpeg_available():
            raise RuntimeError("ffmpeg is not installed on the server.")
        audio = yt.streams.filter(only_audio=True, subtype="mp4").order_by("abr").desc().first()
        if not audio:
            raise ValueError("No MP4 audio stream available to merge with the video.")

    total = video.filesize + (audio.filesize if audio else 0)
    yt.register_on_progress_callback(_progress_tracker(job, total, done_before))

    _set(job, status="downloading")
    video_path = Path(video.download(output_path=str(job.work_dir), filename="video.mp4", skip_existing=False))
    done_before[0] = video.filesize
    filename = f"{clean_title(yt.title)} ({video.resolution}).mp4"

    if not audio:
        _set(job, file_path=video_path, filename=filename, media_type="video/mp4")
        return

    audio_path = Path(audio.download(output_path=str(job.work_dir), filename="audio.m4a", skip_existing=False))

    _set(job, status="merging", progress=99)
    output_path = job.work_dir / "output.mp4"
    result = subprocess.run(
        [FFMPEG, "-nostdin", "-loglevel", "error", "-y",
         "-i", str(video_path), "-i", str(audio_path),
         "-map", "0:v:0", "-map", "1:a:0", "-c", "copy", str(output_path)],
        capture_output=True,
        text=True,
    )
    video_path.unlink(missing_ok=True)
    audio_path.unlink(missing_ok=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr.strip()[-300:]}")

    _set(job, file_path=output_path, filename=filename, media_type="video/mp4")


def _download_audio(job: Job) -> None:
    done_before = [0]
    yt = YouTube(job.video_url)
    audio = yt.streams.get_by_itag(job.itag)
    if not audio or audio.includes_video_track:
        raise ValueError("Selected audio format is not available.")

    yt.register_on_progress_callback(_progress_tracker(job, audio.filesize, done_before))

    _set(job, status="downloading")
    extension = audio_extension(audio)
    path = Path(audio.download(output_path=str(job.work_dir), filename=f"audio.{extension}", skip_existing=False))
    _set(job, file_path=path, filename=f"{clean_title(yt.title)}.{extension}", media_type=f"audio/{audio.subtype}")
