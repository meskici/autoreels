"""Tiny stdlib HTTP helper.

autoreels has no third-party dependencies. Every provider talks through this.
urllib honours HTTP_PROXY / HTTPS_PROXY from the environment, so corporate
and agent proxies work without extra configuration.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any


class HttpError(RuntimeError):
    def __init__(self, status: int, body: str, url: str):
        self.status = status
        self.body = body
        self.url = url
        super().__init__(f"HTTP {status} from {url}: {body[:500]}")


def request(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    json_body: Any = None,
    raw_body: bytes | None = None,
    timeout: int = 120,
    retries: int = 3,
) -> bytes:
    """Perform an HTTP request, retrying on 429/5xx with exponential backoff."""
    headers = dict(headers or {})
    data = raw_body
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")

    last_error: Exception | None = None
    for attempt in range(retries):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")
            if exc.code in (408, 429) or exc.code >= 500:
                last_error = HttpError(exc.code, body, url)
                time.sleep(2**attempt)
                continue
            raise HttpError(exc.code, body, url) from exc
        except urllib.error.URLError as exc:
            last_error = exc
            time.sleep(2**attempt)

    raise last_error if last_error else RuntimeError("request failed")


def get_json(url: str, **kwargs: Any) -> Any:
    return json.loads(request(url, **kwargs).decode("utf-8"))


def post_json(url: str, json_body: Any, **kwargs: Any) -> Any:
    return json.loads(
        request(url, method="POST", json_body=json_body, **kwargs).decode("utf-8")
    )


def download(url: str, dest: str, timeout: int = 120) -> str:
    """Fetch a binary asset to disk. Returns the destination path."""
    payload = request(url, timeout=timeout)
    with open(dest, "wb") as handle:
        handle.write(payload)
    return dest
