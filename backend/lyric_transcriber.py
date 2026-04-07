"""
lyric_transcriber.py

Transcribes audio to timestamped lyric segments using faster-whisper.
Returns a list of {"start": float, "end": float, "text": str} dicts,
one dict per lyric line (grouped by sentence/phrase).
"""

import re
from typing import List, Dict


def _join_words(words: List[str]) -> str:
    text = " ".join(words)
    text = re.sub(r"\s+([,.;!?])", r"\1", text)
    return text.strip()


def _segment_words_into_lines(word_items: List[Dict]) -> List[Dict]:
    """
    Convert per-word timestamps into line-like lyric segments.
    This gives denser, more display-friendly lines than raw Whisper segments.
    """
    if not word_items:
        return []

    lines: List[Dict] = []
    current: List[Dict] = []

    min_words = 3
    max_words = 9
    max_duration = 6.0
    strong_gap = 0.9
    soft_gap = 0.35

    for idx, item in enumerate(word_items):
        current.append(item)
        next_item = word_items[idx + 1] if idx + 1 < len(word_items) else None
        gap = (next_item["start"] - item["end"]) if next_item else None
        duration = current[-1]["end"] - current[0]["start"]
        word_count = len(current)
        token = item["word"]

        should_break = False
        if next_item is None:
            should_break = True
        elif token.endswith((".", "!", "?")) and word_count >= min_words:
            should_break = True
        elif token.endswith(",") and word_count >= min_words and (gap or 0.0) >= soft_gap:
            should_break = True
        elif gap is not None and gap >= strong_gap and word_count >= min_words:
            should_break = True
        elif duration >= max_duration and word_count >= min_words:
            should_break = True
        elif word_count >= max_words and gap is not None and gap >= soft_gap:
            should_break = True

        if should_break:
            text = _join_words([word["word"] for word in current])
            if text:
                lines.append(
                    {
                        "start": round(float(current[0]["start"]), 3),
                        "end": round(float(current[-1]["end"]), 3),
                        "text": text,
                    }
                )
            current = []

    return lines


def transcribe_lyrics(audio_path: str, model_size: str = "base") -> List[Dict]:
    """
    Transcribe the audio at audio_path using Whisper.

    Args:
        audio_path:  Path to the audio file.
        model_size:  Whisper model size. "base" is a good balance of speed/accuracy.
                     Use "small" or "medium" for better quality on noisy recordings.

    Returns:
        [{"start": 4.2, "end": 8.0, "text": "I walked a lonely road"}, ...]
    """
    # Lazy import so the module loads even if faster-whisper isn't installed
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise RuntimeError(
            "faster-whisper is not installed. Run: pip install faster-whisper"
        )

    model = WhisperModel(model_size, device="cpu", compute_type="int8")

    segments, _info = model.transcribe(
        audio_path,
        beam_size=5,
        word_timestamps=True,   # enables per-word timing
        vad_filter=False,       # keep sung phrases that VAD can wrongly drop
        condition_on_previous_text=False,
        language="en",
    )
    segments = list(segments)

    words: List[Dict] = []

    for seg in segments:
        seg_words = getattr(seg, "words", None) or []
        for word in seg_words:
            token = (word.word or "").strip()
            if not token:
                continue
            words.append(
                {
                    "start": float(word.start),
                    "end": float(word.end),
                    "word": token,
                }
            )

    lyric_lines = _segment_words_into_lines(words)
    if lyric_lines:
        return lyric_lines

    # Fallback to segment-level text if word timestamps are unavailable.
    fallback_lines: List[Dict] = []
    for seg in segments:
        text = (seg.text or "").strip()
        if not text:
            continue
        fallback_lines.append(
            {
                "start": round(float(seg.start), 3),
                "end": round(float(seg.end), 3),
                "text": text,
            }
        )

    return fallback_lines
