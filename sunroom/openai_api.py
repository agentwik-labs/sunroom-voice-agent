"""The few OpenAI requests this app makes, and the API key they use."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

from . import config  # noqa: F401  (loads .env before the key is read below)

RETRIES = 3  # rides out a brief network drop

_api_key = os.getenv("OPENAI_API_KEY", "")


def has_api_key() -> bool:
    return _api_key.startswith("sk-") and _api_key != "sk-..."


def use_api_key(key: str) -> None:
    """Check a key by making a request with it, then keep it in memory for this run."""
    global _api_key
    if not key.startswith("sk-"):
        raise ValueError("That doesn't look like an OpenAI API key. It should start with sk-.")
    previous, _api_key = _api_key, key
    try:
        _request("models?limit=1")
    except ValueError:
        _api_key = previous
        raise


def post(path: str, body: dict) -> bytes:
    if not has_api_key():
        raise ValueError("Enter your OpenAI API key first.")
    return _request(path, body)


def _request(path: str, body: dict | None = None) -> bytes:
    request = urllib.request.Request(
        f"https://api.openai.com/v1/{path}",
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {_api_key}", "Content-Type": "application/json"},
    )
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read()
        except urllib.error.HTTPError as err:
            message = json.loads(err.read() or b"{}").get("error", {}).get("message", err.reason)
            raise ValueError(f"OpenAI said: {message}") from err
        except (urllib.error.URLError, TimeoutError) as err:
            if attempt == RETRIES - 1:
                raise ValueError("Can't reach OpenAI. Check the internet connection.") from err
            time.sleep(1 + attempt)
    raise AssertionError("unreachable")
