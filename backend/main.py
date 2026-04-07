import asyncio
import tempfile
import os
import shutil
import librosa
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from chord_detector import detect_chords
from lyric_transcriber import transcribe_lyrics
from aligner import align_chords_to_lyrics
from output_postprocessor import postprocess_analysis_output

app = FastAPI(title="Chord Detection API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_TYPES = {"audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav"}
MAX_FILE_SIZE_MB = 20


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/analyze")
async def analyze_song(
    file: UploadFile | None = File(default=None),
    youtube_url: str | None = Form(default=None),
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
        "duration": 214.5
    }
    """
    youtube_url = (youtube_url or "").strip()
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

    try:
        if file is not None:
            if file.content_type not in ALLOWED_TYPES:
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
            suffix = ".mp3" if "mpeg" in file.content_type or "mp3" in file.content_type else ".wav"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(raw)
                tmp_path = tmp.name
            raw_title = os.path.splitext(file.filename)[0] if file.filename else "Untitled"
        else:
            cleanup_dir = tempfile.mkdtemp(prefix="tuneflow-youtube-")
            tmp_path, raw_title = await asyncio.to_thread(
                _download_youtube_audio,
                youtube_url,
                cleanup_dir,
            )

        # Run chord detection and transcription in parallel
        chords_task = asyncio.to_thread(detect_chords, tmp_path)
        lyrics_task = asyncio.to_thread(transcribe_lyrics, tmp_path)

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
