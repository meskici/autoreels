"""Brand profiles: the voice, rules, and video formats a script is written to."""

from __future__ import annotations

import json
import os
from typing import Any

_DIR = os.path.dirname(os.path.abspath(__file__))


class UnknownBrand(ValueError):
    pass


def available() -> list[str]:
    return sorted(
        name[:-5]
        for name in os.listdir(_DIR)
        if name.endswith(".json")
    )


def load(name_or_path: str) -> dict[str, Any]:
    """Load a brand profile by id (shipped) or by path (your own JSON)."""
    if os.path.exists(name_or_path):
        path = name_or_path
    else:
        path = os.path.join(_DIR, f"{name_or_path}.json")
        if not os.path.exists(path):
            raise UnknownBrand(
                f"unknown brand {name_or_path!r}; available: {', '.join(available())} "
                "(or pass a path to your own brand JSON)"
            )
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def get_format(profile: dict[str, Any], fmt_id: str | None) -> dict[str, Any]:
    """Resolve a format id against a profile, defaulting to the first listed."""
    formats = profile.get("formats") or []
    if not formats:
        raise UnknownBrand(f"brand {profile.get('id')!r} defines no formats")
    if not fmt_id or fmt_id == "auto":
        return formats[0]
    for fmt in formats:
        if fmt["id"] == fmt_id:
            return fmt
    known = ", ".join(f["id"] for f in formats)
    raise UnknownBrand(f"unknown format {fmt_id!r} for brand {profile.get('id')!r}; try: {known}")
