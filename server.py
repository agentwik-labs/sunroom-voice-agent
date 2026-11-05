#!/usr/bin/env python3
"""Sunroom voice agent demo. Run it, then open the address it prints."""
from __future__ import annotations

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from sunroom import calls, openai_api, storage
from sunroom.config import DEFAULT_ENGINE, PORT, WEB_DIR
from sunroom.scenarios import SCENARIOS

ALLOWED_ORIGINS = {f"http://127.0.0.1:{PORT}", f"http://localhost:{PORT}"}
MAX_AUDIO_BYTES = 200 * 1024 * 1024
PAGES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
}


def app_config() -> dict:
    return {
        "tests": [{"id": key, "label": value["label"]} for key, value in SCENARIOS.items()],
        "engines": calls.ENGINES,
        "default_engine": DEFAULT_ENGINE,
        "has_key": openai_api.has_api_key(),
    }


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        route = self.path.split("?")[0]
        if route in PAGES:
            name, content_type = PAGES[route]
            self._send(200, (WEB_DIR / name).read_bytes(), content_type)
        elif route == "/api/records":
            self._json(200, storage.load_all())
        elif route == "/api/config":
            self._json(200, app_config())
        elif route == "/favicon.ico":
            self._send(204, b"", "image/x-icon")
        elif match := re.fullmatch(r"/api/audio/([0-9a-f]{32})", route):
            audio = storage.find_audio(match[1])
            self._send(200, audio, "audio/webm") if audio else self.send_error(404)
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        # Stops other websites from using this server to spend your OpenAI credit.
        if self.headers.get("Origin") not in ALLOWED_ORIGINS:
            return self._json(403, {"error": "Requests are only accepted from this page."})
        length = int(self.headers.get("Content-Length", 0))
        route, _, query = self.path.partition("?")
        try:
            if route == "/api/call/audio":
                self._save_audio(query.removeprefix("session_id="), length)
            else:
                self._json(200, self._handle(route, json.loads(self.rfile.read(length) or b"{}")))
        except ValueError as err:
            self._json(400, {"error": str(err)})

    def _handle(self, route: str, body: dict) -> dict:
        if route == "/api/key":
            openai_api.use_api_key(body.get("key", ""))
            return {"saved": True}
        if route == "/api/session":
            if body.get("engine") == "live":
                return calls.start_live_call(body.get("scenario"), body.get("sdp", ""))
            return calls.start_realtime_call(body.get("scenario"))
        if route == "/api/tool":
            return calls.run_tool(body.get("session_id", ""), body.get("name", ""), body.get("arguments", ""))
        if route == "/api/test/next":
            return calls.next_test_line(body.get("session_id", ""), body.get("transcript", []))
        if route == "/api/call/finish":
            return calls.finish_call(
                body.get("session_id", ""),
                body.get("transcript", []),
                body.get("duration", 0),
                body.get("interruptions", 0),
                body.get("spoken", []),
                body.get("reply_gaps", []),
            )
        raise ValueError("Unknown request.")

    def _save_audio(self, call_id: str, length: int) -> None:
        if not 0 < length <= MAX_AUDIO_BYTES:
            raise ValueError("Recording not accepted.")
        calls.save_recording(call_id, self.rfile.read(length))
        self._json(200, {"saved": True})

    def _json(self, status: int, data) -> None:
        self._send(status, json.dumps(data).encode(), "application/json")

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args) -> None:
        pass  # polling would flood the terminal


if __name__ == "__main__":
    print(f"Open http://127.0.0.1:{PORT}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
