"""
aligner.py

Maps chord segments onto lyric lines by timestamp overlap.
Each lyric line gets a de-duplicated, ordered list of chords
that fall within (or overlap) its time range.
"""

from typing import List, Dict


def align_chords_to_lyrics(
    lyric_segments: List[Dict],
    chord_segments: List[Dict],
) -> List[Dict]:
    """
    Combine lyric lines and chord segments into a single aligned structure.

    Args:
        lyric_segments: [{"start": float, "end": float, "text": str}, ...]
        chord_segments: [{"start": float, "end": float, "chord": str}, ...]

    Returns:
        [
            {
                "start":  4.2,
                "end":    8.1,
                "text":   "I walked a lonely road",
                "chords": ["Am", "G", "F"]
            },
            ...
        ]
    """
    aligned: List[Dict] = []

    for line in lyric_segments:
        line_start = line["start"]
        line_end = line["end"]

        # Collect overlapping chord windows in timeline order.
        overlaps = [
            seg
            for seg in chord_segments
            if seg["start"] < line_end and seg["end"] > line_start
        ]
        overlaps.sort(key=lambda seg: (seg["start"], seg["end"]))

        chords = []
        for seg in overlaps:
            chord = seg["chord"]
            if chord == "N":
                continue
            if not chords or chords[-1] != chord:
                chords.append(chord)

        if len(chords) > 5:
            chords = chords[:5]

        aligned.append({
            "start": line_start,
            "end": line_end,
            "text": line["text"],
            "chords": chords,
        })

    return aligned
