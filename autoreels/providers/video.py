"""Image-to-video adapters.

These animate a still you already own — a real product photo — into a short
clip. They do not generate a product from a text prompt, and autoreels never
asks them to: the input image is always one of the store's own photos.

Two providers ship. Both follow the same shape: submit a job, poll until it
finishes, download the result.

  runway  Runway's image-to-video endpoint (Gen-4 family).
  fal     Kling image-to-video hosted on fal.ai's queue.

Model IDs and endpoints on both services change faster than this file will.
Every one is overridable by environment variable, so a version bump is a config
change rather than a patch — see `.env.example`.
"""

from __future__ import annotations

import base64
import mimetypes
import os
import time
from dataclasses import dataclass

from ..http import HttpError, get_json, post_json, request


class VideoUnavailable(RuntimeError):
    """No provider configured, or the provider refused the job."""


class VideoTimeout(RuntimeError):
    pass


@dataclass
class Clip:
    path: str
    duration: float
    provider: str
    job_id: str = ""


# Providers bill per clip and cap generation at a few fixed lengths.
SUPPORTED_LENGTHS = (5, 10)


def pick_length(seconds: float) -> int:
    """Smallest supported clip length that covers the beat."""
    for length in SUPPORTED_LENGTHS:
        if seconds <= length:
            return length
    return SUPPORTED_LENGTHS[-1]


def _image_reference(image: str) -> str:
    """Providers take a public URL or a data URI. Local files become data URIs."""
    if image.startswith(("http://", "https://")):
        return image
    if not os.path.exists(image):
        raise VideoUnavailable(f"image not found: {image}")
    mime = mimetypes.guess_type(image)[0] or "image/jpeg"
    with open(image, "rb") as handle:
        payload = base64.b64encode(handle.read()).decode("ascii")
    return f"data:{mime};base64,{payload}"


def _download(url: str, dest: str) -> str:
    with open(dest, "wb") as handle:
        handle.write(request(url, timeout=300))
    return dest


# --- Runway -----------------------------------------------------------------


def _runway(image: str, prompt: str, seconds: int, dest: str, cfg) -> Clip:
    headers = {
        "Authorization": f"Bearer {cfg.runway_api_key}",
        "X-Runway-Version": cfg.runway_api_version,
    }
    submitted = post_json(
        f"{cfg.runway_base_url}/v1/image_to_video",
        {
            "model": cfg.runway_model,
            "promptImage": _image_reference(image),
            "promptText": prompt,
            "ratio": cfg.runway_ratio,
            "duration": seconds,
        },
        headers=headers,
        timeout=120,
    )
    job_id = submitted.get("id")
    if not job_id:
        raise VideoUnavailable(f"runway did not return a job id: {submitted}")

    deadline = time.time() + cfg.video_timeout
    while time.time() < deadline:
        time.sleep(cfg.video_poll_seconds)
        task = get_json(f"{cfg.runway_base_url}/v1/tasks/{job_id}", headers=headers)
        status = str(task.get("status", "")).upper()
        if status in ("SUCCEEDED", "COMPLETE", "COMPLETED"):
            output = task.get("output") or []
            url = output[0] if isinstance(output, list) and output else output
            if not url:
                raise VideoUnavailable(f"runway job {job_id} succeeded with no output")
            return Clip(path=_download(url, dest), duration=float(seconds),
                        provider="runway", job_id=job_id)
        if status in ("FAILED", "CANCELLED", "ERROR"):
            raise VideoUnavailable(
                f"runway job {job_id} {status.lower()}: {task.get('failure') or task.get('error') or ''}"
            )
    raise VideoTimeout(f"runway job {job_id} still running after {cfg.video_timeout}s")


# --- Kling, via fal.ai's queue ----------------------------------------------


def _fal(image: str, prompt: str, seconds: int, dest: str, cfg) -> Clip:
    headers = {"Authorization": f"Key {cfg.fal_api_key}"}
    submitted = post_json(
        f"{cfg.fal_base_url}/{cfg.fal_model}",
        {
            "image_url": _image_reference(image),
            "prompt": prompt,
            "duration": str(seconds),
            "aspect_ratio": cfg.fal_aspect_ratio,
        },
        headers=headers,
        timeout=120,
    )
    job_id = submitted.get("request_id", "")
    status_url = submitted.get("status_url")
    response_url = submitted.get("response_url")
    if not status_url or not response_url:
        raise VideoUnavailable(f"fal did not return queue urls: {submitted}")

    deadline = time.time() + cfg.video_timeout
    while time.time() < deadline:
        time.sleep(cfg.video_poll_seconds)
        status = str(get_json(status_url, headers=headers).get("status", "")).upper()
        if status in ("COMPLETED", "OK", "SUCCESS"):
            payload = get_json(response_url, headers=headers)
            video = payload.get("video") or {}
            url = video.get("url") if isinstance(video, dict) else video
            if not url:
                raise VideoUnavailable(f"fal job {job_id} finished with no video: {payload}")
            return Clip(path=_download(url, dest), duration=float(seconds),
                        provider="fal", job_id=job_id)
        if status in ("FAILED", "ERROR", "CANCELLED"):
            raise VideoUnavailable(f"fal job {job_id} {status.lower()}")
    raise VideoTimeout(f"fal job {job_id} still running after {cfg.video_timeout}s")


_ADAPTERS = {"runway": _runway, "fal": _fal}


def animate(image: str, prompt: str, seconds: float, dest_stem: str, cfg) -> Clip:
    """Animate one still. Raises VideoUnavailable rather than returning junk."""
    provider = cfg.resolved_video()
    if provider == "none":
        raise VideoUnavailable(
            "no image-to-video provider configured — "
            "set RUNWAY_API_KEY or FAL_API_KEY (see .env.example)"
        )
    adapter = _ADAPTERS.get(provider)
    if adapter is None:
        raise VideoUnavailable(f"unknown video provider {provider!r}; try: runway, fal")

    length = pick_length(seconds)
    try:
        return adapter(image, prompt, length, f"{dest_stem}.mp4", cfg)
    except HttpError as exc:
        raise VideoUnavailable(f"{provider} rejected the job: {exc}") from exc


def available(cfg) -> str:
    provider = cfg.resolved_video()
    if provider == "none":
        return "none (Ken Burns on stills — set RUNWAY_API_KEY or FAL_API_KEY to animate)"
    model = cfg.runway_model if provider == "runway" else cfg.fal_model
    return f"{provider} ({model})"
