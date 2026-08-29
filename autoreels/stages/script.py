"""Stage 2 — write the script.

Given a product, a brand profile and a format, produce N variants. Each variant
is a beat list: voiceover line, on-screen text, which photo backs it, how long
it holds, and how the camera moves.

With ANTHROPIC_API_KEY set this is written by Claude against the brand's copy
rules. Without one it falls back to a template writer that pulls its sentences
from the product description, so the pipeline still produces a real video.
"""

from __future__ import annotations

import json
import re
from typing import Any

from ..config import Config
from ..models import Beat, Product, Script
from ..providers import llm

SYSTEM = """You write short-form vertical video scripts (Instagram Reels, TikTok) for e-commerce products.

You write to a brand profile and you never break its copy rules. Every factual
claim you make must be traceable to the product description you are given. If
the description does not support a claim, you leave it out rather than invent it.

You return JSON only. No prose before or after."""

PROMPT = """# Brand

Name: {brand_name}
Market: {market}
Language: write ALL copy in {language}.
Positioning: {positioning}
Voice: {voice}

Copy rules (hard constraints):
{copy_rules}

Never use these words or anything equivalent: {banned}

Copy smells to avoid (these are what make writing sound machine-made):
{smells}

Never claim (breaking one of these makes the ad false, not just clumsy):
{never}

{brand_notes}

# Video format: {fmt_label}

{fmt_brief}

Target length: about {target_seconds} seconds across {beat_count} beats.
Voiceover: {vo_mode}

# Product

Title: {title}
Handle: {handle}
Type: {product_type}
Tags: {tags}
Price: {price} {currency}

Description (your ONLY source of product facts):
\"\"\"
{description}
\"\"\"

Available photos, in order — refer to them by index:
{image_list}

# Task

Write {variant_count} distinct script variant(s). Distinct means a genuinely
different opening hook and a different angle of attack, not a reworded version
of the same script.

Rules for beats:
- role is one of: hook, body, proof, cta. Exactly one hook (first) and one cta (last).
- The hook must earn the first two seconds. No greeting, no brand name first.
- voiceover: one spoken sentence. {vo_rule}
- on_screen: a SHORT burned-in text card, at most 6 words. It is not a copy of
  the voiceover — it is the line a viewer with the sound off needs to read.
- image_index: choose the photo that actually shows what the beat talks about.
  A macro beat needs a macro photo. Do not use the same photo for every beat if
  more than one is available.
- duration: seconds, between 1.5 and 6. The sum must land near {target_seconds}.
- motion: one of zoom_in, zoom_out, pan_left, pan_right, static. Vary it.

Also write, per variant:
- caption: the post caption in {language}, conversational, ending in a question.
- hashtags: 4-6, no leading '#', seeded from {hashtag_seeds} plus the motif or product.
- notes: one line on what this variant is testing, and any photo you wish existed.

# Output

Return a JSON array of {variant_count} objects, each exactly:

{{"fmt": "{fmt_id}", "beats": [{{"role": "hook", "voiceover": "...", "on_screen": "...", "image_index": 0, "duration": 2.5, "motion": "zoom_in"}}], "caption": "...", "hashtags": ["..."], "notes": "..."}}"""


def _image_list(product: Product) -> str:
    if not product.images:
        return "(none — the render will fall back to a generated background)"
    lines = []
    for index, image in enumerate(product.images):
        alt = image.alt or "no alt text"
        size = f"{image.width}x{image.height}" if image.width else "unknown size"
        lines.append(f"  [{index}] {alt} ({size})")
    return "\n".join(lines)


def _build_prompt(
    product: Product,
    profile: dict[str, Any],
    fmt: dict[str, Any],
    variant_count: int,
) -> str:
    wants_vo = fmt.get("voiceover", True)
    notes = profile.get("notes") or []
    return PROMPT.format(
        brand_name=profile.get("name") or product.vendor or "(unnamed)",
        market=profile.get("market", ""),
        language=profile.get("language", "en"),
        positioning=profile.get("positioning", ""),
        voice=profile.get("voice", ""),
        copy_rules="\n".join(f"- {rule}" for rule in profile.get("copy_rules", [])),
        banned=", ".join(profile.get("banned_words", [])) or "(none)",
        smells="\n".join(f"- {smell}" for smell in profile.get("copy_smells", []))
               or "- (none listed)",
        never="\n".join(f"- {rule}" for rule in profile.get("never_claim", []))
              or "- (none listed)",
        brand_notes=("Brand notes:\n" + "\n".join(f"- {n}" for n in notes)) if notes else "",
        fmt_label=fmt.get("label", fmt["id"]),
        fmt_brief=fmt.get("brief", ""),
        fmt_id=fmt["id"],
        target_seconds=fmt.get("target_seconds", 20),
        beat_count=fmt.get("beats", 5),
        vo_mode="yes, spoken narration" if wants_vo else "NO voiceover — this format is silent, the text cards carry it",
        vo_rule=(
            "Keep it under 14 words so it fits the beat duration."
            if wants_vo
            else "Leave voiceover as an empty string for every beat."
        ),
        title=product.title,
        handle=product.handle,
        product_type=product.product_type,
        tags=", ".join(product.tags) or "(none)",
        price=product.price,
        currency=product.currency,
        description=product.description or "(no description available)",
        image_list=_image_list(product),
        hashtag_seeds=", ".join(profile.get("hashtag_seeds", [])) or "(none)",
        variant_count=variant_count,
    )


def _coerce(
    raw: dict[str, Any],
    fmt: dict[str, Any],
    profile: dict[str, Any],
    product: Product,
    variant: str,
) -> Script:
    """Trust the model's words, not its arithmetic or its indices."""
    image_count = max(len(product.images), 1)
    valid_motion = {"zoom_in", "zoom_out", "pan_left", "pan_right", "static"}
    beats: list[Beat] = []
    for index, item in enumerate(raw.get("beats") or []):
        role = str(item.get("role") or ("hook" if index == 0 else "body")).lower()
        motion = str(item.get("motion") or "auto").lower()
        try:
            duration = float(item.get("duration", 3.0))
        except (TypeError, ValueError):
            duration = 3.0
        try:
            image_index = int(item.get("image_index", index))
        except (TypeError, ValueError):
            image_index = index
        beats.append(
            Beat(
                role=role if role in {"hook", "body", "proof", "cta"} else "body",
                voiceover=str(item.get("voiceover") or "").strip(),
                on_screen=str(item.get("on_screen") or "").strip(),
                image_index=image_index % image_count,
                duration=min(max(duration, 1.5), 8.0),
                motion=motion if motion in valid_motion else "auto",
            )
        )
    if not beats:
        raise ValueError(f"script variant {variant!r} has no beats")

    hashtags = [str(tag).lstrip("#") for tag in (raw.get("hashtags") or [])][:6]
    if not hashtags:
        hashtags = list(profile.get("hashtag_seeds", []))[:5]

    return Script(
        variant=variant,
        fmt=str(raw.get("fmt") or fmt["id"]),
        language=profile.get("language", "en"),
        beats=beats,
        caption=str(raw.get("caption") or "").strip(),
        hashtags=hashtags,
        notes=str(raw.get("notes") or "").strip(),
    )


# --- keyless fallback -------------------------------------------------------


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text or "")
    return [p.strip() for p in parts if len(p.strip()) > 15]


def _template_scripts(
    product: Product,
    profile: dict[str, Any],
    fmt: dict[str, Any],
    variant_count: int,
) -> list[Script]:
    """Build a serviceable script from the product description alone.

    This is what runs with no API key. It is deliberately plain: it reuses the
    store's own sentences rather than inventing copy, so nothing unverifiable
    reaches the screen.
    """
    lines = _sentences(product.description) or [product.title]
    wants_vo = fmt.get("voiceover", True)
    beat_count = int(fmt.get("beats", 5))
    target = float(fmt.get("target_seconds", 20))
    image_count = max(len(product.images), 1)
    motions = ["zoom_in", "pan_right", "zoom_out", "pan_left", "static"]
    name = product.title.split(" Dekoratif")[0].split(" - ")[0].strip()

    scripts: list[Script] = []
    for variant_index in range(variant_count):
        rotated = lines[variant_index:] + lines[:variant_index]
        body_count = max(beat_count - 2, 1)
        body_lines = (rotated * beat_count)[:body_count]

        beats = [
            Beat(
                role="hook",
                voiceover=name if wants_vo else "",
                on_screen=name,
                image_index=variant_index % image_count,
                duration=2.5,
                motion="zoom_in",
            )
        ]
        for body_index, line in enumerate(body_lines):
            beats.append(
                Beat(
                    role="body",
                    voiceover=line if wants_vo else "",
                    on_screen=" ".join(line.split()[:5]),
                    image_index=(variant_index + body_index + 1) % image_count,
                    duration=(target - 5.0) / body_count,
                    motion=motions[(variant_index + body_index) % len(motions)],
                )
            )
        beats.append(
            Beat(
                role="cta",
                voiceover=profile.get("cta", "") if wants_vo else "",
                on_screen=profile.get("cta", ""),
                image_index=(variant_index + 1) % image_count,
                duration=2.5,
                motion="zoom_out",
            )
        )

        scripts.append(
            Script(
                variant=chr(ord("a") + variant_index),
                fmt=fmt["id"],
                language=profile.get("language", "en"),
                beats=beats,
                caption=(lines[0] if lines else product.title),
                hashtags=list(profile.get("hashtag_seeds", []))[:5],
                notes="Template fallback — set ANTHROPIC_API_KEY for written-to-brief copy.",
            )
        )
    return scripts


def load(
    path: str,
    product: Product,
    profile: dict[str, Any],
    fmt: dict[str, Any],
) -> list[Script]:
    """Read scripts from a file, accepting either shape.

    A saved `script-a.json` round-trips exactly. Raw model output — what you get
    from pasting Claude's answer to the scriptwriting prompt, which carries no
    `variant` and no `language` — is coerced and clamped like a live response.
    """
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, dict):
        payload = [payload]
    if not payload:
        raise ValueError(f"{path} contains no scripts")

    scripts: list[Script] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"{path}: entry {index} is not an object")
        variant = str(item.get("variant") or chr(ord("a") + index))
        if "variant" in item and "language" in item:
            scripts.append(Script.from_dict(item))     # our own saved shape
        else:
            scripts.append(_coerce(item, fmt, profile, product, variant))
    return scripts


def write(
    product: Product,
    profile: dict[str, Any],
    fmt: dict[str, Any],
    config: Config,
    variants: int = 1,
) -> list[Script]:
    """Produce `variants` scripts. Falls back to templates without a key."""
    if not config.anthropic_api_key:
        return _template_scripts(product, profile, fmt, variants)

    response = llm.complete(
        api_key=config.anthropic_api_key,
        base_url=config.anthropic_base_url,
        model=config.model,
        system=SYSTEM,
        prompt=_build_prompt(product, profile, fmt, variants),
        max_tokens=1200 + 900 * variants,
    )
    payload = llm.extract_json(response)
    if isinstance(payload, dict):
        payload = [payload]

    scripts: list[Script] = []
    for index, item in enumerate(payload[:variants]):
        scripts.append(
            _coerce(item, fmt, profile, product, variant=chr(ord("a") + index))
        )
    if not scripts:
        raise ValueError("model returned no usable variants")
    return scripts
