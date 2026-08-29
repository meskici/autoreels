"""Data shapes passed between pipeline stages.

Every stage reads JSON from the run directory and writes JSON back, so a run
can be inspected, hand-edited, and resumed at any stage.
"""

from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass, field
from typing import Any


def _dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


class JsonMixin:
    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)  # type: ignore[arg-type]

    def save(self, path: str) -> str:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(_dumps(self.to_dict()))
        return path

    @classmethod
    def load(cls, path: str):
        with open(path, encoding="utf-8") as handle:
            return cls.from_dict(json.load(handle))

    @classmethod
    def from_dict(cls, data: dict[str, Any]):
        return cls(**data)  # type: ignore[call-arg]


@dataclass
class Image(JsonMixin):
    url: str
    alt: str = ""
    width: int = 0
    height: int = 0
    local_path: str = ""


@dataclass
class Product(JsonMixin):
    """Normalised product, whatever the source was."""

    handle: str
    title: str
    description: str
    price: str = ""
    currency: str = ""
    url: str = ""
    vendor: str = ""
    product_type: str = ""
    tags: list[str] = field(default_factory=list)
    images: list[Image] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Product":
        data = dict(data)
        data["images"] = [Image(**img) for img in data.get("images", [])]
        return cls(**data)

    def series(self) -> str:
        """Best guess at the product family, used to pick a narrative angle."""
        for tag in self.tags:
            if "seri" in tag.lower() or "series" in tag.lower():
                return tag
        return self.product_type or ""


@dataclass
class Beat(JsonMixin):
    """One narrative unit: a chunk of voiceover plus what is on screen for it."""

    role: str                      # hook | body | proof | cta
    voiceover: str = ""            # spoken line (may be empty for silent cuts)
    on_screen: str = ""            # burned-in text card
    image_index: int = 0           # which product photo backs this beat
    duration: float = 3.0          # seconds
    motion: str = "auto"           # zoom_in | zoom_out | pan_left | pan_right | static


@dataclass
class Script(JsonMixin):
    """A complete video script for one variant."""

    variant: str
    fmt: str                       # which of the brand video formats this is
    language: str = "tr"
    beats: list[Beat] = field(default_factory=list)
    caption: str = ""
    hashtags: list[str] = field(default_factory=list)
    notes: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Script":
        data = dict(data)
        data["beats"] = [Beat(**b) for b in data.get("beats", [])]
        return cls(**data)

    def duration(self) -> float:
        return sum(beat.duration for beat in self.beats)

    def voiceover_text(self) -> str:
        return " ".join(b.voiceover.strip() for b in self.beats if b.voiceover.strip())


@dataclass
class Word(JsonMixin):
    """One caption word with its on-screen window."""

    text: str
    start: float
    end: float


@dataclass
class Shot(JsonMixin):
    """A rendered beat: resolved image, resolved timing, resolved caption words."""

    index: int
    image_path: str
    start: float
    duration: float
    motion: str
    on_screen: str
    words: list[Word] = field(default_factory=list)
    audio_path: str = ""
    source_video: str = ""      # provider clip, when this shot was animated
    clip_path: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Shot":
        data = dict(data)
        data["words"] = [Word(**w) for w in data.get("words", [])]
        return cls(**data)


@dataclass
class Storyboard(JsonMixin):
    variant: str
    width: int = 1080
    height: int = 1920
    fps: int = 30
    shots: list[Shot] = field(default_factory=list)
    audio_path: str = ""
    music_path: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Storyboard":
        data = dict(data)
        data["shots"] = [Shot.from_dict(s) for s in data.get("shots", [])]
        return cls(**data)

    def duration(self) -> float:
        return sum(shot.duration for shot in self.shots)
