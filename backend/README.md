# Submission Log 1 - Audio Upload Backend

This snapshot is for backend log 1 and focuses on audio-file uploads only.

## Included

- Express API setup with CORS and Multer
- `GET /api/health`
- `POST /api/analyze` for audio uploads
- Input validation (upload required, YouTube not yet enabled)
- ffmpeg preprocessing to normalize audio into mono 22.05 kHz WAV
- Python librosa analysis (`analyze_audio.py`) returning tempo, key, and chord timeline

## Not included yet

- YouTube download pipeline (`yt-dlp`)

## Run

```bash
npm install
python -m pip install -r requirements.txt
npm run dev
```

### Required tooling

- ffmpeg (Windows example: `winget install Gyan.FFmpeg`)
- Python with dependencies installed from `requirements.txt`
