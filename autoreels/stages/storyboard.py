"""Stages 3 and 4 — voiceover, then storyboard.

Downloads the real product photos, synthesises the voiceover line for each beat,
retimes every beat to the length its narration actually came out at, and lays
out the caption words across that window. The result is a `Storyboard`: a fully
resolved plan the renderer can execute without making a single decision.
"""

from __future__ import annotations

import os
from typing import Any

from ..config import Config
from ..http import download
from ..models import Product, Script, Shot, Storyboard, Word
from ..providers import tts


def _fetch_images(product: Product, dest_dir: str) -> list[str]:
    os.makedirs(dest_dir, exist_ok=True)
    paths: list[str] = []
    for index, image in enumerate(product.images):
        if image.local_path and os.path.exists(image.local_path):
            paths.append(image.local_path)
            continue
        # A url with no scheme is a local file — your own phone shots, or a
        # frame you graded by hand and dropped next to the product JSON.
        if "://" not in image.url:
            local = os.path.abspath(image.url)
            if os.path.exists(local):
                image.local_path = local
                paths.append(local)
                continue
            print(f"  ! image {index} not found on disk: {local}")
            continue

        suffix = os.path.splitext(image.url.split("?")[0])[1] or ".jpg"
        path = os.path.join(dest_dir, f"img{index:02d}{suffix}")
        if not os.path.exists(path):
            try:
                download(image.url, path)
            except Exception as exc:  # noqa: BLE001
                print(f"  ! image {index} failed to download: {exc}")
                continue
        image.local_path = path
        paths.append(path)
    return paths


def _lay_out_words(text: str, start: float, duration: float) -> list[Word]:
    """Spread caption words across the beat, weighted by word length.

    Long words hold longer than short ones, which reads far closer to speech
    than an even split does.
    """
    words = [w for w in (text or "").split() if w]
    if not words or duration <= 0:
        return []
    weights = [len(w) + 1 for w in words]
    total = sum(weights)
    out: list[Word] = []
    cursor = start
    for word, weight in zip(words, weights):
        span = duration * weight / total
        out.append(Word(text=word, start=round(cursor, 3), end=round(cursor + span, 3)))
        cursor += span
    return out


def _motion_for(beat_motion: str, index: int) -> str:
    if beat_motion and beat_motion != "auto":
        return beat_motion
    cycle = ["zoom_in", "pan_right", "zoom_out", "pan_left"]
    return cycle[index % len(cycle)]


def build(
    script: Script,
    product: Product,
    config: Config,
    run_dir: str,
    music: str = "",
) -> Storyboard:
    """Resolve one script into a renderable storyboard."""
    images = _fetch_images(product, os.path.join(run_dir, "images"))
    if not images:
        raise RuntimeError(
            "no product images available — nothing to render. "
            "Check the image URLs in product.json."
        )

    audio_dir = os.path.join(run_dir, f"audio-{script.variant}")
    os.makedirs(audio_dir, exist_ok=True)

    shots: list[Shot] = []
    cursor = 0.0
    for index, beat in enumerate(script.beats):
        speech = tts.speak(beat.voiceover, os.path.join(audio_dir, f"beat{index:02d}"), config)

        # The beat holds for as long as the narration needs, plus breathing room,
        # but never less than the script asked for.
        duration = max(beat.duration, speech.duration + 0.6 if speech.duration else 0.0)
        duration = round(min(duration, 12.0), 3)

        caption_source = beat.on_screen or beat.voiceover
        shot = Shot(
            index=index,
            image_path=images[beat.image_index % len(images)],
            start=round(cursor, 3),
            duration=duration,
            motion=_motion_for(beat.motion, index),
            on_screen=beat.on_screen,
            words=_lay_out_words(caption_source, cursor, duration),
            audio_path=speech.path,
        )
        shots.append(shot)
        cursor += duration

    board = Storyboard(
        variant=script.variant,
        width=config.width,
        height=config.height,
        fps=config.fps,
        shots=shots,
        music_path=music,
    )
    return board


def audio_segments(board: Storyboard) -> list[tuple[str, float, float]]:
    """(path, start, duration) for each beat's narration, for the mixer."""
    return [
        (shot.audio_path, shot.start, shot.duration)
        for shot in board.shots
        if shot.audio_path
    ]


def summarise(board: Storyboard, script: Script) -> dict[str, Any]:
    return {
        "variant": board.variant,
        "format": script.fmt,
        "duration": round(board.duration(), 2),
        "shots": len(board.shots),
        "distinct_images": len({shot.image_path for shot in board.shots}),
    }
