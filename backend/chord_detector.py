"""
chord_detector.py

Detect chords from an audio file using harmonic chroma features.
Returns [{"start": float, "end": float, "chord": str}, ...].
"""

from typing import Dict, List, Sequence, Tuple

import librosa
import numpy as np


NOTES_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
NOTES_FLAT = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]

# Krumhansl-Schmuckler key profiles.
KS_MAJOR_PROFILE = np.array(
    [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88],
    dtype=float,
)
KS_MINOR_PROFILE = np.array(
    [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17],
    dtype=float,
)


def _build_templates(note_names: Sequence[str]) -> List[Dict]:
    """Build major, minor, dominant 7th and minor 7th templates for all roots."""
    templates = []

    chord_types = [
        ("", [0, 4, 7]),      # major triad
        ("m", [0, 3, 7]),     # minor triad
        ("7", [0, 4, 7, 10]), # dominant seventh
        ("m7", [0, 3, 7, 10]) # minor seventh
    ]

    for root_idx, root_name in enumerate(note_names):
        for suffix, intervals in chord_types:
            vec = np.zeros(12, dtype=float)
            for interval in intervals:
                vec[(root_idx + interval) % 12] = 1.0
            vec /= np.linalg.norm(vec)
            templates.append({"name": f"{root_name}{suffix}", "vec": vec})

    return templates


TEMPLATES_SHARP = _build_templates(NOTES_SHARP)
TEMPLATES_FLAT = _build_templates(NOTES_FLAT)
NOTE_TO_PC = {
    "C": 0,
    "B#": 0,
    "C#": 1,
    "Db": 1,
    "D": 2,
    "D#": 3,
    "Eb": 3,
    "E": 4,
    "Fb": 4,
    "E#": 5,
    "F": 5,
    "F#": 6,
    "Gb": 6,
    "G": 7,
    "G#": 8,
    "Ab": 8,
    "A": 9,
    "A#": 10,
    "Bb": 10,
    "B": 11,
    "Cb": 11,
}


def _pitch_distance(a: int, b: int) -> int:
    diff = abs(a - b) % 12
    return min(diff, 12 - diff)


def _parse_chord(chord_name: str) -> Tuple[int, str] | None:
    """Parse chord text into pitch class and quality ('major' or 'minor')."""
    if chord_name == "N":
        return None

    if chord_name.endswith("m"):
        root = chord_name[:-1]
        quality = "minor"
    else:
        root = chord_name
        quality = "major"

    pitch_class = NOTE_TO_PC.get(root)
    if pitch_class is None:
        return None

    return pitch_class, quality


def _allowed_chords_for_key(key_root: int, key_mode: str, use_flats: bool) -> List[str]:
    """Build a practical in-key chord vocabulary (triads only)."""
    note_names = NOTES_FLAT if use_flats else NOTES_SHARP

    if key_mode == "major":
        major_degrees = [0, 5, 7]      # I, IV, V
        minor_degrees = [2, 4, 9]      # ii, iii, vi
        dim_degrees = [11]             # vii* (diminished 7th)
    else:
        major_degrees = [3, 8, 10]     # III, VI, VII
        minor_degrees = [0, 5, 7]      # i, iv, v
        dim_degrees = [2]              # ii* (diminished 2nd)

    major_chords = [note_names[(key_root + degree) % 12] for degree in major_degrees]
    minor_chords = [f"{note_names[(key_root + degree) % 12]}m" for degree in minor_degrees]
    dim_chords = [f"{note_names[(key_root + degree) % 12]}dim" for degree in dim_degrees]

    # Keep ii and vi strongly represented for pop progressions.
    return major_chords + minor_chords + dim_chords


def _coerce_to_allowed_chord(chord_name: str, allowed_chords: List[str]) -> str:
    """Project noisy detections to the nearest practical in-key chord."""
    parsed = _parse_chord(chord_name)
    if parsed is None:
        return chord_name

    source_pc, source_quality = parsed
    best_chord = chord_name
    best_cost = float("inf")

    for candidate in allowed_chords:
        if candidate.endswith("dim"):
            candidate_quality = "diminished"
            candidate_root = candidate[:-3]
        elif candidate.endswith("m"):
            candidate_quality = "minor"
            candidate_root = candidate[:-1]
        else:
            candidate_quality = "major"
            candidate_root = candidate

        candidate_pc = NOTE_TO_PC.get(candidate_root)
        if candidate_pc is None:
            continue

        distance_cost = _pitch_distance(source_pc, candidate_pc)
        quality_cost = 0.0
        if source_quality != candidate_quality:
            quality_cost = 1.25 if candidate_quality != "diminished" else 2.0

        total_cost = distance_cost + quality_cost
        if total_cost < best_cost:
            best_cost = total_cost
            best_chord = candidate

    return best_chord


def _detect_key(chroma: np.ndarray) -> Tuple[int, str]:
    """
    Detect key root and mode using Krumhansl-Schmuckler profiles.
    Returns: (root_pitch_class, "major" | "minor")
    """
    chroma_mean = chroma.mean(axis=1)
    norm = np.linalg.norm(chroma_mean)
    if norm < 1e-8:
        return 0, "major"

    chroma_unit = chroma_mean / norm

    best_score = float("-inf")
    best_root = 0
    best_mode = "major"

    for root in range(12):
        major_profile = np.roll(KS_MAJOR_PROFILE, root)
        major_profile /= np.linalg.norm(major_profile)
        major_score = float(np.dot(chroma_unit, major_profile))

        if major_score > best_score:
            best_score = major_score
            best_root = root
            best_mode = "major"

        minor_profile = np.roll(KS_MINOR_PROFILE, root)
        minor_profile /= np.linalg.norm(minor_profile)
        minor_score = float(np.dot(chroma_unit, minor_profile))

        if minor_score > best_score:
            best_score = minor_score
            best_root = root
            best_mode = "minor"

    return best_root, best_mode


def _should_use_flats(key_root: int, key_mode: str) -> bool:
    """Choose enharmonic spelling based on the detected key."""
    if key_mode == "major":
        return key_root in {5, 10, 3, 8, 1, 6}  # F, Bb, Eb, Ab, Db, Gb
    return key_root in {2, 7, 0, 5, 10, 3, 8}  # Dm, Gm, Cm, Fm, Bbm, Ebm, Abm


def _simplify_chord(chord_name: str) -> str:
    """Reduce seventh chords to triads."""
    if chord_name == "N":
        return chord_name
    if chord_name.endswith("7"):
        return chord_name[:-1]
    return chord_name


def _match_chord(chroma_window: np.ndarray, templates: List[Dict]) -> str:
    """Return the highest-cosine-similarity chord for the window."""
    norm = np.linalg.norm(chroma_window)
    if norm < 0.01:
        return "N"

    unit = chroma_window / norm
    best_score = -1.0
    best_name = "N"

    for template in templates:
        score = float(np.dot(unit, template["vec"]))
        if score > best_score:
            best_score = score
            best_name = template["name"]

    return _simplify_chord(best_name)


def _smooth_chords(raw_chords: List[Dict]) -> List[Dict]:
    """Majority-vote smoothing with a sliding window of 3 frames."""
    if not raw_chords:
        return []

    smoothed: List[Dict] = []
    for i in range(len(raw_chords)):
        window = raw_chords[max(0, i - 1): min(len(raw_chords), i + 2)]
        counts: Dict[str, int] = {}
        for seg in window:
            chord = seg["chord"]
            counts[chord] = counts.get(chord, 0) + 1

        max_count = max(counts.values())
        candidates = [chord for chord, count in counts.items() if count == max_count]

        center_chord = raw_chords[i]["chord"]
        if center_chord in candidates:
            selected = center_chord
        else:
            selected = next(seg["chord"] for seg in window if seg["chord"] in candidates)

        new_seg = raw_chords[i].copy()
        new_seg["chord"] = selected
        smoothed.append(new_seg)

    return smoothed


def detect_chords(
    audio_path: str,
    window_seconds: float = 1.0,
    sr: int = 22050,
) -> List[Dict]:
    """
    Analyse audio_path and return chord segments.
    Returns: [{"start": 0.0, "end": 2.5, "chord": "Am"}, ...]
    """
    y, sr = librosa.load(audio_path, sr=sr, mono=True)

    hop_length = 512
    y_harmonic, _ = librosa.effects.hpss(y)
    chroma = librosa.feature.chroma_cqt(y=y_harmonic, sr=sr, hop_length=hop_length)

    key_root, key_mode = _detect_key(chroma)
    use_flats = _should_use_flats(key_root, key_mode)
    templates = TEMPLATES_FLAT if use_flats else TEMPLATES_SHARP
    allowed_chords = _allowed_chords_for_key(key_root, key_mode, use_flats)

    frames_per_window = max(1, int(window_seconds * sr / hop_length))
    n_frames = chroma.shape[1]
    duration = librosa.get_duration(y=y, sr=sr)

    raw_chords = []
    for start_frame in range(0, n_frames, frames_per_window):
        end_frame = min(start_frame + frames_per_window, n_frames)
        window = chroma[:, start_frame:end_frame].mean(axis=1)
        chord_name = _match_chord(window, templates)
        chord_name = _coerce_to_allowed_chord(chord_name, allowed_chords)

        start_time = librosa.frames_to_time(start_frame, sr=sr, hop_length=hop_length)
        end_time = min(
            librosa.frames_to_time(end_frame, sr=sr, hop_length=hop_length),
            duration,
        )
        raw_chords.append(
            {
                "start": round(float(start_time), 3),
                "end": round(float(end_time), 3),
                "chord": chord_name,
            }
        )

    smoothed_chords = _smooth_chords(raw_chords)
    return _merge_segments(smoothed_chords)


def _merge_segments(raw: List[Dict]) -> List[Dict]:
    if not raw:
        return []

    merged = [raw[0].copy()]
    for seg in raw[1:]:
        if seg["chord"] == merged[-1]["chord"]:
            merged[-1]["end"] = seg["end"]
        else:
            merged.append(seg.copy())

    return merged
