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
- `POST /analyze` (multipart/form-data, field name: `file`)

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
