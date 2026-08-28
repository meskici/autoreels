"""Anthropic Messages API client (stdlib only).

Used by the script stage. When no key is present the script stage falls back
to its template writer instead of calling this.
"""

from __future__ import annotations

import json
import re
from typing import Any

from ..http import post_json


class LLMUnavailable(RuntimeError):
    pass


def complete(
    *,
    api_key: str,
    base_url: str,
    model: str,
    system: str,
    prompt: str,
    max_tokens: int = 4000,
    temperature: float = 1.0,
) -> str:
    if not api_key:
        raise LLMUnavailable("no ANTHROPIC_API_KEY set")
    payload = post_json(
        f"{base_url}/v1/messages",
        {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
        },
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        timeout=180,
    )
    parts = [
        block.get("text", "")
        for block in payload.get("content", [])
        if block.get("type") == "text"
    ]
    return "".join(parts).strip()


def extract_json(text: str) -> Any:
    """Pull the first JSON object or array out of a model response."""
    fenced = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    if fenced:
        text = fenced.group(1)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError(f"no JSON found in model response: {text[:400]}")
