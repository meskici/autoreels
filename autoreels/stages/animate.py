"""Optional stage — animate selected stills into real clips.

Runs between the storyboard and the render. Only the shots you select are sent
to the provider, because these services bill per clip: `--animate hook` sends
one, which is usually where the money is best spent anyway.

Every prompt is written to *preserve* the photographed object. These models
happily redraw whatever they are given, and a redrawn lamp is a lie about a
product someone is about to buy. When a shot fails, or the provider is not
configured, that shot silently keeps its Ken Burns move — an animated reel with
three real clips and two pans is still a reel.
"""

from __future__ import annotations

import os
from typing import Any

from ..config import Config
from ..models import Product, Storyboard
from ..providers import video

CAMERA = {
    "zoom_in": "very slow push in toward the object",
    "zoom_out": "very slow pull back from the object",
    "pan_left": "very slow lateral drift to the left",
    "pan_right": "very slow lateral drift to the right",
    "pan_up": "very slow tilt upward",
    "pan_down": "very slow tilt downward",
    "static": "camera almost still, only the faintest drift",
}


def select(spec: str, shot_count: int) -> set[int]:
    """Resolve --animate into the set of shot indices to send.

    Accepts: none, hook, all, or a comma-separated list of indices ("0,3").
    """
    spec = (spec or "none").strip().lower()
    if spec in ("", "none", "off", "0"):
        return set()
    if spec == "hook":
        return {0} if shot_count else set()
    if spec == "all":
        return set(range(shot_count))
    chosen: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if not part.lstrip("-").isdigit():
            raise ValueError(
                f"--animate takes none, hook, all, or shot indices like 0,2 — got {spec!r}"
            )
        index = int(part)
        if 0 <= index < shot_count:
            chosen.add(index)
    return chosen


def build_prompt(on_screen: str, motion: str, product: Product, profile: dict[str, Any]) -> str:
    """A motion prompt anchored on not changing the product."""
    camera = CAMERA.get(motion, CAMERA["static"])
    hint = (profile.get("animation") or {}).get("prompt_hint", "")
    subject = product.title.split(" Dekoratif")[0].split(" - ")[0].strip() or "the product"
    parts = [
        f"{camera}.",
        f"{subject} keeps its exact shape, geometry, proportions, texture and colour.",
        "Do not redraw, restyle or invent any part of the object.",
        "No new objects, no people, no text.",
    ]
    if hint:
        parts.append(hint)
    if on_screen:
        parts.append(f"Mood: {on_screen}.")
    return " ".join(parts)


def risky(product: Product, profile: dict[str, Any]) -> str:
    """Why animating this product is a bad idea, or '' when it is fine."""
    animation = profile.get("animation") or {}
    avoid = set(animation.get("avoid_tags") or [])
    if avoid & set(product.tags):
        return animation.get("avoid_reason", "this brand marks the product as risky to animate")
    return ""


def run(
    board: Storyboard,
    product: Product,
    profile: dict[str, Any],
    config: Config,
    run_dir: str,
    spec: str = "none",
    say=print,
) -> list[str]:
    """Animate the selected shots in place. Returns warnings."""
    warnings: list[str] = []
    targets = select(spec, len(board.shots))
    if not targets:
        return warnings

    provider = config.resolved_video()
    if provider == "none":
        warnings.append(
            "--animate was requested but no video provider is configured; "
            "every shot kept its Ken Burns move"
        )
        return warnings

    caution = risky(product, profile)
    if caution:
        warnings.append(f"animating {product.handle!r}: {caution}")

    out_dir = os.path.join(run_dir, f"animated-{board.variant}")
    os.makedirs(out_dir, exist_ok=True)

    for index in sorted(targets):
        shot = board.shots[index]
        prompt = build_prompt(shot.on_screen, shot.motion, product, profile)
        try:
            clip = video.animate(
                shot.image_path, prompt, shot.duration,
                os.path.join(out_dir, f"shot{index:02d}"), config,
            )
        except (video.VideoUnavailable, video.VideoTimeout) as exc:
            warnings.append(f"shot {index} not animated ({exc}); kept its Ken Burns move")
            continue
        shot.source_video = clip.path
        say(f"    animated shot {index} via {clip.provider} -> {os.path.basename(clip.path)}")

    return warnings
