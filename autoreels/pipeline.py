"""Orchestration: product in, finished Reels out.

The pipeline writes every intermediate to a run directory so you can inspect
what the machine decided, hand-edit it, and re-run only the stage you changed:

    runs/<handle>-<timestamp>/
      product.json          stage 1 — what the store says
      script-a.json         stage 2 — beats, captions, hashtags (one per variant)
      storyboard-a.json     stages 3+4 — resolved photos, timings, word windows
      images/               downloaded product photos
      audio-a/              per-beat narration
      work-a/               clips, captions.ass, mixed audio
      <handle>-a.mp4        stage 5 — the deliverable
      run.json              summary of the whole run
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any

from . import brand
from .config import Config
from .models import Product, Script, Storyboard
from .providers import shopify, tts
from .stages import render as render_stage
from .stages import script as script_stage
from .stages import storyboard as storyboard_stage


@dataclass
class RunResult:
    run_dir: str
    product: Product
    scripts: list[Script] = field(default_factory=list)
    boards: list[Storyboard] = field(default_factory=list)
    videos: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _slug(text: str) -> str:
    keep = [c if c.isalnum() or c in "-_" else "-" for c in text.lower()]
    return "".join(keep).strip("-") or "product"


def make_run_dir(config: Config, handle: str) -> str:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    path = os.path.join(config.runs_dir, f"{_slug(handle)}-{stamp}")
    os.makedirs(path, exist_ok=True)
    return path


def ingest(config: Config, handle: str = "", product_json: str = "") -> Product:
    """Stage 1. Prefer an explicit JSON file, else hit the Admin API."""
    if product_json:
        return shopify.load_json(product_json)
    if not handle:
        raise ValueError("give a product handle or --product-json")
    return shopify.fetch(config.shopify_store, config.shopify_token, handle,
                         config.shopify_api_version)


def run(
    config: Config,
    *,
    handle: str = "",
    product_json: str = "",
    brand_id: str = "",
    fmt_id: str = "auto",
    variants: int = 1,
    music: str = "",
    render: bool = True,
    run_dir: str = "",
    script_json: str = "",
    quiet: bool = False,
) -> RunResult:
    say = (lambda *a: None) if quiet else print
    profile = brand.load(brand_id or config.brand)
    fmt = brand.get_format(profile, fmt_id)

    product = ingest(config, handle=handle, product_json=product_json)
    if run_dir:
        os.makedirs(run_dir, exist_ok=True)
    else:
        run_dir = make_run_dir(config, product.handle or handle or "product")
    result = RunResult(run_dir=run_dir, product=product)

    product.save(os.path.join(run_dir, "product.json"))
    say(f"1/5 ingest      {product.title}  ({len(product.images)} photos)")

    if not product.images:
        result.warnings.append("product has no photos — the render will fail")

    needs = fmt.get("needs", "")
    if needs and len(product.images) < 3:
        result.warnings.append(
            f"format {fmt['id']!r} wants: {needs} — only {len(product.images)} photo(s) available"
        )

    # --- stage 2 -----------------------------------------------------------
    if script_json:
        result.scripts = script_stage.load(script_json, product, profile, fmt)
        say(f"2/5 script      loaded {len(result.scripts)} variant(s) from {script_json}")
    else:
        result.scripts = script_stage.write(product, profile, fmt, config, variants=variants)
        writer = "claude" if config.anthropic_api_key else "template fallback"
        say(f"2/5 script      {len(result.scripts)} variant(s), format={fmt['id']} via {writer}")

    for item in result.scripts:
        item.save(os.path.join(run_dir, f"script-{item.variant}.json"))

    # --- stages 3 + 4 ------------------------------------------------------
    say(f"3/5 voiceover   provider={tts.available(config)}")
    for item in result.scripts:
        board = storyboard_stage.build(item, product, config, run_dir, music=music)
        board.save(os.path.join(run_dir, f"storyboard-{item.variant}.json"))
        result.boards.append(board)
        summary = storyboard_stage.summarise(board, item)
        say(
            f"4/5 storyboard  variant {board.variant}: "
            f"{summary['shots']} shots, {summary['distinct_images']} distinct photos, "
            f"{summary['duration']}s"
        )

    # --- stage 5 -----------------------------------------------------------
    if render:
        for item, board in zip(result.scripts, result.boards):
            dest = os.path.join(run_dir, f"{_slug(product.handle)}-{board.variant}.mp4")
            path = render_stage.render(board, config, run_dir, dest)
            board.save(os.path.join(run_dir, f"storyboard-{board.variant}.json"))
            result.videos.append(path)
            say(f"5/5 render      {path}")
    else:
        say("5/5 render      skipped (--no-render)")

    _write_summary(result, profile, fmt, config)
    return result


def _write_summary(result: RunResult, profile: dict[str, Any], fmt: dict[str, Any], config: Config) -> None:
    payload = {
        "product": {
            "handle": result.product.handle,
            "title": result.product.title,
            "url": result.product.url,
            "photos": len(result.product.images),
        },
        "brand": profile.get("id"),
        "format": fmt.get("id"),
        "tts": config.resolved_tts(),
        "scriptwriter": "claude" if config.anthropic_api_key else "template",
        "variants": [
            {
                "variant": item.variant,
                "duration": round(item.duration(), 2),
                "caption": item.caption,
                "hashtags": item.hashtags,
                "notes": item.notes,
                "video": video,
            }
            for item, video in zip(
                result.scripts, result.videos + [""] * len(result.scripts)
            )
        ],
        "warnings": result.warnings,
    }
    with open(os.path.join(result.run_dir, "run.json"), "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
