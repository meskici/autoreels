"""Text-to-speech adapters.

Every adapter takes a line of text and returns an audio file plus its real
duration. `none` writes silence sized to a reading-speed estimate, which keeps
the rest of the pipeline identical whether or not a voice key is present.
"""

from __future__ import annotations

import os
import subprocess
import wave
from dataclasses import dataclass

from ..http import request


@dataclass
class Speech:
    path: str
    duration: float
    silent: bool = False


# Words per second for a natural read. Turkish and English both sit near this.
WORDS_PER_SECOND = 2.6


def estimate_duration(text: str, minimum: float = 0.8) -> float:
    words = len([w for w in text.split() if w.strip()])
    return max(words / WORDS_PER_SECOND, minimum) if words else 0.0


def _write_silence(path: str, seconds: float, rate: int = 44100) -> str:
    frames = int(max(seconds, 0.05) * rate)
    with wave.open(path, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(b"\x00\x00" * frames)
    return path


def probe_duration(path: str, ffprobe: str = "ffprobe") -> float:
    """Real duration of an audio file, or 0.0 if ffprobe is unavailable."""
    try:
        out = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True, check=True,
        )
        return float(out.stdout.strip())
    except (OSError, subprocess.CalledProcessError, ValueError):
        return 0.0


def _elevenlabs(text: str, dest: str, cfg) -> str:
    url = (
        f"https://api.elevenlabs.io/v1/text-to-speech/{cfg.elevenlabs_voice_id}"
        "?output_format=mp3_44100_128"
    )
    audio = request(
        url,
        method="POST",
        headers={"xi-api-key": cfg.elevenlabs_api_key, "Accept": "audio/mpeg"},
        json_body={
            "text": text,
            "model_id": cfg.elevenlabs_model,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        },
        timeout=180,
    )
    with open(dest, "wb") as handle:
        handle.write(audio)
    return dest


def _openai(text: str, dest: str, cfg) -> str:
    audio = request(
        "https://api.openai.com/v1/audio/speech",
        method="POST",
        headers={"Authorization": f"Bearer {cfg.openai_api_key}"},
        json_body={
            "model": cfg.openai_tts_model,
            "voice": cfg.openai_tts_voice,
            "input": text,
            "response_format": "mp3",
        },
        timeout=180,
    )
    with open(dest, "wb") as handle:
        handle.write(audio)
    return dest


def speak(text: str, dest_stem: str, cfg) -> Speech:
    """Synthesise one line. `dest_stem` is a path without extension."""
    text = (text or "").strip()
    provider = cfg.resolved_tts()

    if not text or provider == "none":
        seconds = estimate_duration(text) if text else 0.0
        path = _write_silence(f"{dest_stem}.wav", max(seconds, 0.1))
        return Speech(path=path, duration=seconds, silent=True)

    dest = f"{dest_stem}.mp3"
    try:
        if provider == "elevenlabs":
            _elevenlabs(text, dest, cfg)
        elif provider == "openai":
            _openai(text, dest, cfg)
        else:
            raise ValueError(f"unknown TTS provider {provider!r}")
    except Exception as exc:  # noqa: BLE001 — never let TTS kill a render
        print(f"  ! TTS ({provider}) failed, falling back to silence: {exc}")
        seconds = estimate_duration(text)
        return Speech(path=_write_silence(f"{dest_stem}.wav", seconds), duration=seconds, silent=True)

    duration = probe_duration(dest, cfg.ffprobe) or estimate_duration(text)
    return Speech(path=dest, duration=duration, silent=False)


def available(cfg) -> str:
    provider = cfg.resolved_tts()
    if provider == "none":
        return "none (silent — set ELEVENLABS_API_KEY or OPENAI_API_KEY for narration)"
    return provider
