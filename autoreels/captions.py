"""Burned-in captions, as ASS.

One dialogue event per word: the whole line stays on screen and the word being
spoken is lifted in the accent colour. That is the caption style short-form
video has converged on, and it survives being watched with the sound off.
"""

from __future__ import annotations

import os
from typing import Iterable

from .models import Shot

HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,{font},{size},&H00FFFFFF,&H00FFFFFF,&H00101010,&H80000000,-1,0,0,0,100,100,0,0,1,{outline},{shadow},2,{margin_h},{margin_h},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

# Accent applied to the word currently being spoken. ASS colours are &HBBGGRR.
ACCENT = "&H0064D2FF&"  # warm amber, reads on both dark and light frames


def _timestamp(seconds: float) -> str:
    seconds = max(seconds, 0.0)
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{int(hours)}:{int(minutes):02d}:{secs:05.2f}"


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def _wrap(words: list[str], char_budget: int, max_words: int = 3) -> list[list[int]]:
    """Group word indices into caption lines.

    Grouping by word count alone overflows the frame the moment a long word
    turns up — Turkish produces plenty of those. Break on a character budget as
    well, and never let a group exceed `max_words`.
    """
    groups: list[list[int]] = []
    current: list[int] = []
    width = 0
    for index, word in enumerate(words):
        addition = len(word) + (1 if current else 0)
        if current and (width + addition > char_budget or len(current) >= max_words):
            groups.append(current)
            current, width = [], 0
            addition = len(word)
        current.append(index)
        width += addition
    if current:
        groups.append(current)
    return groups


def build(
    shots: Iterable[Shot],
    dest: str,
    *,
    width: int = 1080,
    height: int = 1920,
    font: str = "DejaVu Sans",
) -> str:
    """Write an .ass file covering every shot's caption words."""
    size = int(height * 0.042)          # ~80px at 1920
    margin_h = 80
    # A bold sans glyph advances roughly half its point size. Budget lines
    # against the usable width so nothing runs off the edge of a 9:16 frame.
    char_budget = max(int((width - 2 * margin_h) / (size * 0.52)), 8)
    lines = [
        HEADER.format(
            width=width,
            height=height,
            font=font,
            size=size,
            outline=max(int(size * 0.07), 4),
            shadow=2,
            margin_v=int(height * 0.20),
            margin_h=margin_h,
        )
    ]

    for shot in shots:
        if not shot.words:
            continue
        texts = [_escape(word.text) for word in shot.words]
        for group in _wrap(texts, char_budget):
            for position in group:
                word = shot.words[position]
                parts = []
                for i in group:
                    if i == position:
                        parts.append(f"{{\\c{ACCENT}}}{texts[i]}{{\\c&H00FFFFFF&}}")
                    else:
                        parts.append(texts[i])
                body = "{\\fad(60,0)}" + " ".join(parts)
                lines.append(
                    f"Dialogue: 0,{_timestamp(word.start)},{_timestamp(word.end)},"
                    f"Caption,,0,0,0,,{body}"
                )

    os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    return dest
