# TuneFlow Backend (FastAPI)

This backend uses FastAPI for audio upload, chord detection, lyric transcription, and chord-to-lyric alignment.

## Files

- `main.py` - API server and endpoints
- `chord_detector.py` - chord segmentation from audio
- `lyric_transcriber.py` - lyric timestamps using faster-whisper
- `aligner.py` - aligns chord segments to lyric lines

## Setup

```bash
python -m pip install -r requirements.txt
```

## Run

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Endpoints

- `GET /health`
- `GET /health/details` (uptime, dependency checks, cache stats)
- `GET /analysis/options` (supported models, file limits, tuning ranges)
- `POST /analyze` (multipart/form-data)
  - Inputs:
    - `file` (MP3/WAV upload) or `youtube_url` (provide only one)
    - `transcription_model` (optional, default: `base`)
    - `chord_window_seconds` (optional, default: `1.0`, range: `0.25` to `4.0`)
  - Output now includes an `analysis_meta` object with cache/process metadata.

## Runtime Config

Optional environment variables:

- `TUNEFLOW_CACHE_TTL_SECONDS` (default: `1800`)
- `TUNEFLOW_CACHE_MAX_ITEMS` (default: `32`)

## AI Assistance Disclosure (Backend)

The backend was developed with AI-assisted support for difficult implementation and debugging tasks.
AI support was used in these areas:

1. Building and refining the backend pipeline flow in `main.py`.
2. Lyric transcription handling and related processing in `lyric_transcriber.py`.
3. Chord extraction and edge-case handling in `chord_detector.py`.
4. Timestamp and line alignment and formatting logic in `aligner.py` and `output_postprocessor.py`.
5. Evaluation and debugging support for output quality checks in `evaluate_perfect.py`.

AI was used to generate drafts, suggest fixes, and help debug errors.
Final integration decisions, code review, testing, and submitted output were completed by me.
