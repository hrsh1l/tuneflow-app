from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional


CHORD_TOKEN_RE = re.compile(
    r"([A-G](?:#|b)?(?:m|maj7|m7|7|sus2|sus4|dim|aug)?(?:/[A-G](?:#|b)?)?)"
)
CHORD_LINE_RE = re.compile(
    r"^\s*(?:[A-G](?:#|b)?(?:m|maj7|m7|7|sus2|sus4|dim|aug)?(?:/[A-G](?:#|b)?)?\s*)+$"
)
SECTION_RE = re.compile(r"^\[(.+)\]$")
PC_BY_ROOT = {
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
ROOT_BY_PC_FLAT = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]


@dataclass
class ReferenceLine:
    section: str
    chord_line: str
    chords: List[str]
    text: str


@dataclass
class SongReference:
    song: str
    artist: str
    key: str
    lines: List[ReferenceLine]


def _fix_mojibake(text: str) -> str:
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
    }
    fixed = text
    for source, target in replacements.items():
        fixed = fixed.replace(source, target)
    return fixed


def normalize_text(text: str) -> str:
    cleaned = _fix_mojibake(text).lower()
    cleaned = re.sub(r"[^a-z0-9\s]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def normalize_chord(chord: str) -> str:
    chord = chord.strip()
    if not chord or chord == "N":
        return "N"

    match = re.match(r"^([A-G](?:#|b)?)(.*)$", chord)
    if not match:
        return chord

    root = match.group(1)
    suffix = match.group(2)
    pc = PC_BY_ROOT.get(root)
    if pc is None:
        return chord

    is_minor = suffix.startswith("m") and not suffix.startswith("maj")
    canonical_root = ROOT_BY_PC_FLAT[pc]
    return f"{canonical_root}m" if is_minor else canonical_root


def chords_equal(a: str, b: str) -> bool:
    return normalize_chord(a) == normalize_chord(b)


def is_chord_line(line: str) -> bool:
    return bool(CHORD_LINE_RE.match(line.strip()))


def parse_reference_song(path: str | Path) -> SongReference:
    raw = Path(path).read_text(encoding="utf-8", errors="ignore")
    raw = _fix_mojibake(raw)
    lines = [line.rstrip() for line in raw.splitlines()]

    song = "Unknown"
    artist = "Unknown"
    key = "Unknown"
    section = "Song"
    parsed_lines: List[ReferenceLine] = []
    i = 0

    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        if line.startswith("SONG:"):
            song = line.split(":", 1)[1].strip()
            i += 1
            continue
        if line.startswith("ARTIST:"):
            artist = line.split(":", 1)[1].strip()
            i += 1
            continue
        if line.startswith("KEY:"):
            key = line.split(":", 1)[1].strip()
            i += 1
            continue

        section_match = SECTION_RE.match(line)
        if section_match:
            section = section_match.group(1).strip()
            i += 1
            continue

        if is_chord_line(line):
            chord_line = line.rstrip()
            chords = CHORD_TOKEN_RE.findall(chord_line)
            lyric_text = ""

            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines):
                candidate = lines[j].strip()
                if not SECTION_RE.match(candidate) and not is_chord_line(candidate):
                    lyric_text = candidate
                    i = j

            parsed_lines.append(
                ReferenceLine(
                    section=section,
                    chord_line=chord_line,
                    chords=chords,
                    text=lyric_text,
                )
            )

        i += 1

    return SongReference(song=song, artist=artist, key=key, lines=parsed_lines)


def render_chord_line(chords: List[str], lyric: str) -> str:
    if not chords:
        return ""
    if not lyric.strip():
        return "   ".join(chords)

    word_matches = list(re.finditer(r"\S+", lyric))
    if not word_matches:
        return "   ".join(chords)

    starts = [match.start() for match in word_matches]
    width = max(len(lyric), starts[-1] + len(chords[-1]) + 2)
    chars = [" "] * (width + 8)

    for index, chord in enumerate(chords):
        if len(chords) == 1:
            anchor_idx = 0
        else:
            anchor_idx = round(index * (len(starts) - 1) / (len(chords) - 1))
        pos = starts[anchor_idx]
        while pos + len(chord) < len(chars) and any(chars[pos + k] != " " for k in range(len(chord))):
            pos += 1
        for k, char in enumerate(chord):
            chars[pos + k] = char

    return "".join(chars).rstrip()


def build_sections(lines: List[Dict]) -> List[Dict]:
    sections: List[Dict] = []
    current_name: Optional[str] = None
    current_lines: List[Dict] = []

    for line in lines:
        section_name = line.get("section", "Song")
        if current_name != section_name:
            if current_lines:
                sections.append({"name": current_name, "lines": current_lines})
            current_name = section_name
            current_lines = []
        current_lines.append(line)

    if current_lines:
        sections.append({"name": current_name, "lines": current_lines})

    return sections


def _line_similarity(a: str, b: str) -> float:
    a_norm = normalize_text(a)
    b_norm = normalize_text(b)
    if not a_norm and not b_norm:
        return 1.0
    return SequenceMatcher(None, a_norm, b_norm).ratio()


def reference_match_score(reference: SongReference, title: str, lyric_segments: List[Dict]) -> float:
    score = 0.0
    title_norm = normalize_text(title)
    if normalize_text(reference.song) and normalize_text(reference.song) in title_norm:
        score += 0.6
    if normalize_text(reference.artist) and normalize_text(reference.artist) in title_norm:
        score += 0.2

    ref_lyrics = [line.text for line in reference.lines if line.text][:6]
    hyp_lyrics = [line.get("text", "") for line in lyric_segments][:6]
    if ref_lyrics and hyp_lyrics:
        paired = min(len(ref_lyrics), len(hyp_lyrics))
        avg = sum(_line_similarity(ref_lyrics[i], hyp_lyrics[i]) for i in range(paired)) / paired
        score += 0.2 * avg

    return score


def _interpolate(a: float, b: float, ratio: float) -> float:
    return a + (b - a) * ratio


def align_reference_times(reference: SongReference, lyric_segments: List[Dict], duration: float) -> List[Dict]:
    ref_lines = reference.lines
    ref_count = len(ref_lines)
    if ref_count == 0:
        return []

    if not lyric_segments:
        line_dur = max(1.0, duration / max(1, ref_count))
        output = []
        for i, line in enumerate(ref_lines):
            start = round(i * line_dur, 3)
            end = round(min(duration, (i + 1) * line_dur), 3)
            output.append(
                {
                    "start": start,
                    "end": end,
                    "text": line.text,
                    "chords": line.chords,
                    "section": line.section,
                    "chord_line": line.chord_line or render_chord_line(line.chords, line.text),
                }
            )
        return output

    mapped_idx: Dict[int, int] = {}
    search_start = 0
    for i, ref_line in enumerate(ref_lines):
        if not ref_line.text:
            continue
        best_j = -1
        best_score = 0.0
        upper = min(len(lyric_segments), search_start + 10)
        for j in range(search_start, upper):
            score = _line_similarity(ref_line.text, lyric_segments[j].get("text", ""))
            if score > best_score:
                best_score = score
                best_j = j
        if best_j >= 0 and best_score >= 0.35:
            mapped_idx[i] = best_j
            search_start = best_j + 1

    starts: List[Optional[float]] = [None] * ref_count
    ends: List[Optional[float]] = [None] * ref_count
    for i, j in mapped_idx.items():
        starts[i] = float(lyric_segments[j]["start"])
        ends[i] = float(lyric_segments[j]["end"])

    mapped_positions = sorted(mapped_idx.keys())
    if not mapped_positions:
        first_start = float(lyric_segments[0]["start"])
        last_end = max(duration, float(lyric_segments[-1]["end"]))
        for i in range(ref_count):
            starts[i] = _interpolate(first_start, last_end, i / ref_count)
            ends[i] = _interpolate(first_start, last_end, (i + 1) / ref_count)
    else:
        for i in range(ref_count):
            if starts[i] is not None:
                continue
            left = [p for p in mapped_positions if p < i]
            right = [p for p in mapped_positions if p > i]
            if left and right:
                l = left[-1]
                r = right[0]
                ratio = (i - l) / (r - l)
                starts[i] = _interpolate(starts[l], starts[r], ratio)
                ends[i] = _interpolate(ends[l], ends[r], ratio)
            elif left:
                l = left[-1]
                avg_dur = max(1.2, (ends[l] - starts[l]))
                starts[i] = ends[l] + (i - l - 1) * avg_dur
                ends[i] = starts[i] + avg_dur
            elif right:
                r = right[0]
                avg_dur = max(1.2, (ends[r] - starts[r]))
                ends[i] = max(0.0, starts[r] - (r - i - 1) * avg_dur)
                starts[i] = max(0.0, ends[i] - avg_dur)

    output: List[Dict] = []
    for i, ref_line in enumerate(ref_lines):
        start = max(0.0, float(starts[i] if starts[i] is not None else 0.0))
        end = float(ends[i] if ends[i] is not None else start + 1.5)
        if end <= start:
            end = start + 0.5
        start = min(start, duration)
        end = min(max(end, start + 0.2), duration)
        output.append(
            {
                "start": round(start, 3),
                "end": round(end, 3),
                "text": ref_line.text,
                "chords": ref_line.chords,
                "section": ref_line.section,
                "chord_line": ref_line.chord_line or render_chord_line(ref_line.chords, ref_line.text),
            }
        )

    return output


def render_formatted_output(song: str, artist: str, key: str, lines: List[Dict]) -> str:
    out: List[str] = [f"SONG: {song}", f"ARTIST: {artist}", f"KEY: {key}", ""]
    current_section: Optional[str] = None
    for line in lines:
        section = line.get("section", "Song")
        if section != current_section:
            if current_section is not None:
                out.append("")
            out.append(f"[{section}]")
            current_section = section
        chord_line = line.get("chord_line") or render_chord_line(line.get("chords", []), line.get("text", ""))
        if chord_line:
            out.append(chord_line)
        text = line.get("text", "").strip()
        if text:
            out.append(text)
    return "\n".join(out).strip() + "\n"
