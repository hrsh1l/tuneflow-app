import os
import asyncio
import importlib.util
import shutil
import tempfile
from collections import OrderedDict
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from threading import Lock
from time import monotonic, time
from urllib.parse import parse_qsl, urlparse

import librosa
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from chord_detector import detect_chords
from lyric_transcriber import SUPPORTED_TRANSCRIPTION_MODELS, transcribe_lyrics
from aligner import align_chords_to_lyrics
from output_postprocessor import postprocess_analysis_output

app = FastAPI(title="Chord Detection API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_TYPES = {"audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav"}
ALLOWED_EXTENSIONS = {".mp3", ".wav"}
MAX_FILE_SIZE_MB = 20
DEFAULT_TRANSCRIPTION_MODEL = "base"
DEFAULT_CHORD_WINDOW_SECONDS = 1.0
MIN_CHORD_WINDOW_SECONDS = 0.25
MAX_CHORD_WINDOW_SECONDS = 4.0
APP_START_MONOTONIC = monotonic()


def _read_positive_int_env(var_name: str, default: int) -> int:
    raw = os.getenv(var_name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


class AnalysisCache:
    def __init__(self, ttl_seconds: int, max_items: int) -> None:
        self.ttl_seconds = max(1, ttl_seconds)
        self.max_items = max(1, max_items)
        self._lock = Lock()
        self._store: OrderedDict[str, tuple[float, dict]] = OrderedDict()

    def get(self, key: str) -> dict | None:
        now = time()
        with self._lock:
            self._purge_expired_locked(now)
            item = self._store.get(key)
            if item is None:
                return None

            expires_at, payload = item
            if expires_at <= now:
                self._store.pop(key, None)
                return None

            self._store.move_to_end(key)
            return deepcopy(payload)

    def set(self, key: str, payload: dict) -> None:
        now = time()
        with self._lock:
            self._purge_expired_locked(now)
            self._store[key] = (now + self.ttl_seconds, deepcopy(payload))
            self._store.move_to_end(key)
            while len(self._store) > self.max_items:
                self._store.popitem(last=False)

    def stats(self) -> dict:
        now = time()
        with self._lock:
            self._purge_expired_locked(now)
            return {
                "enabled": True,
                "ttl_seconds": self.ttl_seconds,
                "max_items": self.max_items,
                "items": len(self._store),
            }

    def _purge_expired_locked(self, now: float) -> None:
        expired_keys = [
            key for key, (expires_at, _payload) in self._store.items() if expires_at <= now
        ]
        for key in expired_keys:
            self._store.pop(key, None)


ANALYSIS_CACHE = AnalysisCache(
    ttl_seconds=_read_positive_int_env("TUNEFLOW_CACHE_TTL_SECONDS", 1800),
    max_items=_read_positive_int_env("TUNEFLOW_CACHE_MAX_ITEMS", 32),
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/health/details")
async def health_details():
    return {
        "status": "ok",
        "uptime_seconds": round(monotonic() - APP_START_MONOTONIC, 3),
        "cache": ANALYSIS_CACHE.stats(),
        "dependencies": {
            "faster_whisper": _is_module_available("faster_whisper"),
            "yt_dlp": _is_module_available("yt_dlp"),
        },
    }


@app.get("/analysis/options")
async def analysis_options():
    return {
        "allowed_mime_types": sorted(ALLOWED_TYPES),
        "allowed_extensions": sorted(ALLOWED_EXTENSIONS),
        "max_file_size_mb": MAX_FILE_SIZE_MB,
        "transcription_models": sorted(SUPPORTED_TRANSCRIPTION_MODELS),
        "default_transcription_model": DEFAULT_TRANSCRIPTION_MODEL,
        "chord_window_seconds": {
            "default": DEFAULT_CHORD_WINDOW_SECONDS,
            "min": MIN_CHORD_WINDOW_SECONDS,
            "max": MAX_CHORD_WINDOW_SECONDS,
        },
        "cache": ANALYSIS_CACHE.stats(),
    }


@app.post("/analyze")
async def analyze_song(
    file: UploadFile | None = File(default=None),
    youtube_url: str | None = Form(default=None),
    transcription_model: str = Form(default=DEFAULT_TRANSCRIPTION_MODEL),
    chord_window_seconds: float = Form(default=DEFAULT_CHORD_WINDOW_SECONDS),
):
    """
    Accepts an MP3/WAV file or a YouTube URL and returns chords aligned to lyrics.

    Response shape:
    {
        "lines": [
            {
                "start": 4.2,
                "end": 8.1,
                "text": "I walked a lonely road",
                "chords": ["Am", "G", "F"]
            },
            ...
        ],
        "title": "Untitled",
        "duration": 214.5,
        "analysis_meta": {
            "cache_hit": false,
            "transcription_model": "base",
            "chord_window_seconds": 1.0
        }
    }
    """
    youtube_url = (youtube_url or "").strip()
    transcription_model = (transcription_model or DEFAULT_TRANSCRIPTION_MODEL).strip().lower()

    if transcription_model not in SUPPORTED_TRANSCRIPTION_MODELS:
        raise HTTPException(
            status_code=422,
            detail=(
                "Unsupported transcription_model. "
                f"Supported values: {', '.join(sorted(SUPPORTED_TRANSCRIPTION_MODELS))}."
            ),
        )

    if not (MIN_CHORD_WINDOW_SECONDS <= chord_window_seconds <= MAX_CHORD_WINDOW_SECONDS):
        raise HTTPException(
            status_code=422,
            detail=(
                "chord_window_seconds must be between "
                f"{MIN_CHORD_WINDOW_SECONDS} and {MAX_CHORD_WINDOW_SECONDS}."
            ),
        )

    if file is None and not youtube_url:
        raise HTTPException(
            status_code=400,
            detail="Provide either an audio file or a YouTube URL.",
        )

    if file is not None and youtube_url:
        raise HTTPException(
            status_code=400,
            detail="Provide only one source: either file upload or YouTube URL.",
        )

    tmp_path = ""
    cleanup_dir = ""
    raw_title = "Untitled"
    source_type = "file" if file is not None else "youtube"
    processing_start = monotonic()
    cache_key = ""

    try:
        if file is not None:
            file_content_type = (file.content_type or "").lower()
            suffix = _resolve_audio_suffix(file.filename or "", file_content_type)
            if file_content_type not in ALLOWED_TYPES and suffix not in ALLOWED_EXTENSIONS:
                raise HTTPException(
                    status_code=415,
                    detail=f"Unsupported file type: {file.content_type}. Upload an MP3 or WAV.",
                )

            raw = await file.read()
            if len(raw) > MAX_FILE_SIZE_MB * 1024 * 1024:
                raise HTTPException(
                    status_code=413,
                    detail=f"File exceeds {MAX_FILE_SIZE_MB} MB limit.",
                )

            # Write to a temp file so both librosa and Whisper can read from disk.
            cache_key = _build_cache_key(
                source_fingerprint=f"file:{sha256(raw).hexdigest()}",
                transcription_model=transcription_model,
                chord_window_seconds=chord_window_seconds,
            )
            cached_payload = ANALYSIS_CACHE.get(cache_key)
            if cached_payload is not None:
                cached_payload["analysis_meta"] = {
                    **cached_payload.get("analysis_meta", {}),
                    "cache_hit": True,
                    "served_at_utc": _utc_now_iso(),
                }
                return JSONResponse(content=cached_payload)

            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(raw)
                tmp_path = tmp.name
            raw_title = os.path.splitext(file.filename)[0] if file.filename else "Untitled"
        else:
            normalized_youtube_url = _normalize_youtube_url(youtube_url)
            cache_key = _build_cache_key(
                source_fingerprint=f"youtube:{normalized_youtube_url}",
                transcription_model=transcription_model,
                chord_window_seconds=chord_window_seconds,
            )
            cached_payload = ANALYSIS_CACHE.get(cache_key)
            if cached_payload is not None:
                cached_payload["analysis_meta"] = {
                    **cached_payload.get("analysis_meta", {}),
                    "cache_hit": True,
                    "served_at_utc": _utc_now_iso(),
                }
                return JSONResponse(content=cached_payload)

            cleanup_dir = tempfile.mkdtemp(prefix="tuneflow-youtube-")
            tmp_path, raw_title = await asyncio.to_thread(
                _download_youtube_audio,
                normalized_youtube_url,
                cleanup_dir,
            )

        # Run chord detection and transcription in parallel.
        chords_task = asyncio.to_thread(
            detect_chords,
            tmp_path,
            chord_window_seconds,
        )
        lyrics_task = asyncio.to_thread(
            transcribe_lyrics,
            tmp_path,
            transcription_model,
        )

        chord_segments, lyric_segments = await asyncio.gather(chords_task, lyrics_task)
        duration = librosa.get_duration(path=tmp_path)

        aligned = align_chords_to_lyrics(lyric_segments, chord_segments)
        postprocessed = postprocess_analysis_output(
            title=raw_title,
            duration=duration,
            lyric_segments=lyric_segments,
            aligned_lines=aligned,
            chord_segments=chord_segments,
        )

        postprocessed["analysis_meta"] = {
            "cache_hit": False,
            "source_type": source_type,
            "transcription_model": transcription_model,
            "chord_window_seconds": round(chord_window_seconds, 3),
            "processed_at_utc": _utc_now_iso(),
            "processing_seconds": round(monotonic() - processing_start, 3),
        }
        ANALYSIS_CACHE.set(cache_key, postprocessed)
        return JSONResponse(content=postprocessed)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if cleanup_dir:
            shutil.rmtree(cleanup_dir, ignore_errors=True)
        elif tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _is_module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_audio_suffix(filename: str, content_type: str) -> str:
    lowered_name = (filename or "").lower()
    lowered_type = (content_type or "").lower()
    if lowered_type in {"audio/wav", "audio/x-wav"} or lowered_name.endswith(".wav"):
        return ".wav"
    if lowered_type in {"audio/mpeg", "audio/mp3"} or lowered_name.endswith(".mp3"):
        return ".mp3"
    return ""


def _build_cache_key(
    source_fingerprint: str,
    transcription_model: str,
    chord_window_seconds: float,
) -> str:
    raw = (
        f"{source_fingerprint}|"
        f"transcription_model={transcription_model}|"
        f"chord_window_seconds={round(chord_window_seconds, 3)}"
    )
    return sha256(raw.encode("utf-8")).hexdigest()


def _normalize_youtube_url(youtube_url: str) -> str:
    cleaned = (youtube_url or "").strip()
    if not cleaned:
        return cleaned

    parsed = urlparse(cleaned)
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]

    video_id = ""
    if host == "youtu.be":
        video_id = parsed.path.strip("/")
    elif host in {"youtube.com", "m.youtube.com", "music.youtube.com"}:
        path = parsed.path.strip("/")
        if path == "watch":
            query = dict(parse_qsl(parsed.query))
            video_id = query.get("v", "")
        elif path.startswith("shorts/"):
            video_id = path.split("/", 1)[1]
        elif path.startswith("embed/"):
            video_id = path.split("/", 1)[1]

    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"
    return cleaned


def _download_youtube_audio(youtube_url: str, output_dir: str) -> tuple[str, str]:
    try:
        from yt_dlp import YoutubeDL
    except ImportError as import_error:
        raise RuntimeError("yt-dlp is not installed. Run: pip install yt-dlp") from import_error

    output_template = os.path.join(output_dir, "youtube_audio.%(ext)s")
    ydl_options = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }

    try:
        with YoutubeDL(ydl_options) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
            downloaded_path = ydl.prepare_filename(info)
    except Exception as error:
        raise RuntimeError(f"Failed to download YouTube audio: {error}") from error

    base_path, _ = os.path.splitext(downloaded_path)
    audio_path = f"{base_path}.mp3"

    if not os.path.exists(audio_path):
        candidates = [
            os.path.join(output_dir, name)
            for name in os.listdir(output_dir)
            if os.path.isfile(os.path.join(output_dir, name))
        ]
        if not candidates:
            raise RuntimeError("No audio file was downloaded from the YouTube URL.")
        audio_path = max(candidates, key=os.path.getmtime)

    title = (info.get("title") or os.path.splitext(os.path.basename(audio_path))[0]).strip()
    return audio_path, title or "Untitled"
