"""Command line interface.

    autoreels make kumiko-asanoha --variants 3
    autoreels make --product-json product.json --format lights_off
    autoreels script kumiko-asanoha            # script + storyboard, no render
    autoreels render runs/<run>/storyboard-a.json
    autoreels formats --brand kapya
    autoreels doctor
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys

from . import __version__, brand
from .config import Config
from .models import Product, Script, Storyboard
from .providers import tts
from .stages import render as render_stage


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("handle", nargs="?", default="", help="Shopify product handle")
    parser.add_argument("--product-json", default="",
                        help="read the product from a JSON file instead of the Shopify API")
    parser.add_argument("--brand", default="", help="brand profile id or path to a brand JSON")
    parser.add_argument("--format", dest="fmt", default="auto",
                        help="video format id (see `autoreels formats`)")
    parser.add_argument("--variants", type=int, default=1,
                        help="how many distinct scripts to produce")
    parser.add_argument("--music", default="", help="path to a music bed (mp3/m4a/wav)")
    parser.add_argument("--script-json", default="",
                        help="skip scriptwriting and use this script (or list of scripts)")
    parser.add_argument("--out", default="", help="run directory (default: runs/<handle>-<time>)")


def _report(result) -> None:
    print()
    for script, video in zip(result.scripts, result.videos + [""] * len(result.scripts)):
        print(f"── variant {script.variant} ─ {script.fmt} ─ {script.duration():.1f}s")
        for beat in script.beats:
            line = beat.voiceover or beat.on_screen
            print(f"   [{beat.role:5}] {beat.duration:4.1f}s  {line}")
        if script.caption:
            print(f"   caption: {script.caption}")
        if script.hashtags:
            print(f"   tags:    {' '.join('#' + tag for tag in script.hashtags)}")
        if script.notes:
            print(f"   notes:   {script.notes}")
        if video:
            print(f"   video:   {video}")
        print()
    for warning in result.warnings:
        print(f"warning: {warning}")
    print(f"run: {result.run_dir}")


def cmd_make(args, config: Config) -> int:
    from .pipeline import run

    result = run(
        config,
        handle=args.handle,
        product_json=args.product_json,
        brand_id=args.brand,
        fmt_id=args.fmt,
        variants=max(args.variants, 1),
        music=args.music,
        render=not args.no_render,
        run_dir=args.out,
        script_json=args.script_json,
    )
    _report(result)
    return 0


def cmd_script(args, config: Config) -> int:
    args.no_render = True
    return cmd_make(args, config)


def cmd_render(args, config: Config) -> int:
    board = Storyboard.load(args.storyboard)
    run_dir = os.path.dirname(os.path.abspath(args.storyboard))
    if args.music:
        board.music_path = args.music
    dest = args.dest or os.path.join(run_dir, f"render-{board.variant}.mp4")
    print(render_stage.render(board, config, run_dir, dest))
    return 0


def cmd_formats(args, config: Config) -> int:
    profile = brand.load(args.brand or config.brand)
    print(f"{profile.get('name') or profile['id']} — language {profile.get('language')}")
    for fmt in profile["formats"]:
        default = "  (default)" if fmt is profile["formats"][0] else ""
        voice = "voiceover" if fmt.get("voiceover", True) else "silent"
        print(f"\n  {fmt['id']}{default}")
        print(f"    {fmt['label']} — {fmt['target_seconds']}s, {fmt['beats']} beats, {voice}")
        print(f"    needs: {fmt.get('needs', '')}")
    print(f"\nbrands available: {', '.join(brand.available())}")
    return 0


def cmd_doctor(args, config: Config) -> int:
    def status(ok: bool) -> str:
        return "ok  " if ok else "MISS"

    ffmpeg_path = shutil.which(config.ffmpeg)
    checks = [
        (status(bool(ffmpeg_path)), "ffmpeg", ffmpeg_path or "not on PATH — render stage unavailable"),
        (status(bool(shutil.which(config.ffprobe))), "ffprobe", shutil.which(config.ffprobe) or "not on PATH"),
        (status(bool(config.shopify_store and config.shopify_token)), "shopify",
         "Admin API configured" if config.shopify_token else "use --product-json instead"),
        (status(bool(config.anthropic_api_key)), "claude",
         config.model if config.anthropic_api_key else "no key — template scriptwriter"),
        ("ok  ", "voice", tts.available(config)),
        ("ok  ", "brands", ", ".join(brand.available())),
    ]
    print(f"autoreels {__version__}\n")
    for state, name, detail in checks:
        print(f"  [{state}] {name:9} {detail}")
    return 0 if ffmpeg_path else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="autoreels",
        description="Product URL in, vertical Reel out.",
    )
    parser.add_argument("--version", action="version", version=f"autoreels {__version__}")
    parser.add_argument("--env", default=".env", help="path to the env file")
    sub = parser.add_subparsers(dest="command", required=True)

    make = sub.add_parser("make", help="run the whole pipeline and render the video")
    _add_common(make)
    make.add_argument("--no-render", action="store_true", help="stop before the render stage")
    make.set_defaults(func=cmd_make)

    script = sub.add_parser("script", help="script and storyboard only, no render")
    _add_common(script)
    script.set_defaults(func=cmd_script)

    render = sub.add_parser("render", help="render an existing storyboard JSON")
    render.add_argument("storyboard")
    render.add_argument("--music", default="")
    render.add_argument("--dest", default="")
    render.set_defaults(func=cmd_render)

    formats = sub.add_parser("formats", help="list the video formats a brand defines")
    formats.add_argument("--brand", default="")
    formats.set_defaults(func=cmd_formats)

    doctor = sub.add_parser("doctor", help="check what is configured and what is missing")
    doctor.set_defaults(func=cmd_doctor)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = Config.from_env(args.env)
    try:
        return args.func(args, config)
    except (ValueError, LookupError, RuntimeError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
