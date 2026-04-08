#!/usr/bin/env python3
import argparse
import json
import os
import sys
import warnings

import numpy as np

try:
    import librosa
except Exception as import_error:  # pragma: no cover
    print(json.dumps({"error": f"librosa import failed: {import_error}"}))
    sys.exit(1)

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
MAJOR_TEMPLATE = np.array([1.0, 0.0, 0.0, 0.0, 0.8, 0.0, 0.0, 0.7, 0.0, 0.0, 0.0, 0.0])
MINOR_TEMPLATE = np.array([1.0, 0.0, 0.0, 0.7, 0.0, 0.0, 0.0, 0.7, 0.0, 0.0, 0.0, 0.0])

# Keep backend logs clean when librosa falls back to audioread for formats
# that libsndfile cannot decode directly (for example some web streams).
warnings.filterwarnings(
    "ignore",
    message=r"PySoundFile failed\. Trying audioread instead\.",
    category=UserWarning,
    module=r"librosa\.core\.audio",
)
warnings.filterwarnings(
    "ignore",
    message=r"librosa\.core\.audio\.__audioread_load Deprecated as of librosa version .*",
    category=FutureWarning,
    module=r"librosa\.core\.audio",
)


def detect_frame_chord(chroma_frame: np.ndarray):
    frame_sum = float(np.sum(chroma_frame))
    if frame_sum <= 1e-6:
        return "N", 0.0

    normalized = chroma_frame / frame_sum
    best_label = "N"
    best_score = 0.0

    for root in range(12):
        major_score = float(np.dot(normalized, np.roll(MAJOR_TEMPLATE, root)))
        minor_score = float(np.dot(normalized, np.roll(MINOR_TEMPLATE, root)))

        if major_score > best_score:
            best_score = major_score
            best_label = NOTE_NAMES[root]

        if minor_score > best_score:
            best_score = minor_score
            best_label = f"{NOTE_NAMES[root]}m"

    return best_label, min(1.0, best_score)


def compress_chords(frame_chords, frame_confidences, hop_length, sample_rate, min_duration=0.5):
    segments = []

    if not frame_chords:
        return segments

    current_chord = frame_chords[0]
    start_frame = 0
    confidence_values = [frame_confidences[0]]

    for index in range(1, len(frame_chords)):
        chord = frame_chords[index]
        if chord == current_chord:
            confidence_values.append(frame_confidences[index])
            continue

        segments.append(
            {
                "chord": current_chord,
                "startSec": start_frame * hop_length / sample_rate,
                "endSec": index * hop_length / sample_rate,
                "confidence": float(np.mean(confidence_values)),
            }
        )

        current_chord = chord
        start_frame = index
        confidence_values = [frame_confidences[index]]

    segments.append(
        {
            "chord": current_chord,
            "startSec": start_frame * hop_length / sample_rate,
            "endSec": len(frame_chords) * hop_length / sample_rate,
            "confidence": float(np.mean(confidence_values)),
        }
    )

    merged_segments = []
    for segment in segments:
        duration = segment["endSec"] - segment["startSec"]

        if duration < min_duration and merged_segments:
            previous = merged_segments[-1]
            previous["endSec"] = segment["endSec"]
            previous["confidence"] = float(np.mean([previous["confidence"], segment["confidence"]]))
            continue

        merged_segments.append(segment)

    return merged_segments


def estimate_key(chroma_mean: np.ndarray):
    if float(np.sum(chroma_mean)) <= 1e-6:
        return "Unknown"

    key_index = int(np.argmax(chroma_mean))
    return NOTE_NAMES[key_index]


def analyze_audio(file_path: str):
    sample_rate = 22050
    hop_length = 512

    y, sr = librosa.load(file_path, sr=sample_rate, mono=True)

    if len(y) == 0:
        raise ValueError("Audio file appears to be empty.")

    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    tempo_array = np.asarray(tempo).reshape(-1)
    tempo_value = float(tempo_array[0]) if tempo_array.size else 0.0
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop_length)

    frame_chords = []
    frame_confidences = []

    for frame_index in range(chroma.shape[1]):
        chord, confidence = detect_frame_chord(chroma[:, frame_index])
        frame_chords.append(chord)
        frame_confidences.append(confidence)

    segments = compress_chords(frame_chords, frame_confidences, hop_length, sr)
    filtered_segments = [segment for segment in segments if segment["chord"] != "N"]

    chord_progression = []
    for segment in filtered_segments:
        chord = segment["chord"]
        if not chord_progression or chord_progression[-1] != chord:
            chord_progression.append(chord)

    return {
        "durationSec": round(float(librosa.get_duration(y=y, sr=sr)), 2),
        "tempoBpm": round(tempo_value, 2),
        "key": estimate_key(np.mean(chroma, axis=1)),
        "chordProgression": chord_progression[:24],
        "chords": [
            {
                "chord": segment["chord"],
                "startSec": round(segment["startSec"], 2),
                "endSec": round(segment["endSec"], 2),
                "confidence": round(segment["confidence"], 3),
            }
            for segment in filtered_segments[:120]
        ],
        "analysisNotes": [
            "Chord detection uses librosa chroma features and basic major/minor templates.",
            "This is a first-pass estimate and may miss extended or ambiguous harmony.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="Analyze chords from an audio source.")
    parser.add_argument("--input", required=True, help="Path to the audio file")
    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(json.dumps({"error": f"Input file not found: {args.input}"}))
        sys.exit(1)

    try:
        result = analyze_audio(args.input)
    except Exception as analysis_error:
        print(json.dumps({"error": str(analysis_error)}))
        sys.exit(1)

    print(json.dumps(result))


if __name__ == "__main__":
    main()
