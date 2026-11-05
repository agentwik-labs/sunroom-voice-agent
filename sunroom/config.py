"""Settings, read from the environment and an optional .env file."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        name, separator, value = line.strip().partition("=")
        if separator and not name.startswith("#"):
            os.environ.setdefault(name.strip(), value.strip().strip("\"'"))


_load_env_file(ROOT / ".env")

COMPANY = os.getenv("COMPANY_NAME", "Front Range Sunrooms")
DEFAULT_ENGINE = os.getenv("VOICE_ENGINE", "live")
REALTIME_MODEL = os.getenv("OPENAI_REALTIME_MODEL", "gpt-realtime-2.1")
VOICE = os.getenv("OPENAI_VOICE", "marin")
PORT = int(os.getenv("PORT", "8770"))

LIVE_MODEL = "gpt-live-1"
LIVE_BACKEND_MODEL = "gpt-5.6-luna"
TRANSCRIPTION_MODEL = "gpt-4o-transcribe"
ANALYSIS_MODEL = "gpt-4.1"
TEST_CALLER_MODEL = "gpt-4o-mini"
TEST_CALLER_VOICE_MODEL = "gpt-4o-mini-tts"

# Medium gives people room to pause without long silences.
TURN_DETECTION = {"type": "semantic_vad", "eagerness": "medium", "create_response": True, "interrupt_response": True}

RECORDS_DIR = ROOT / "records"  # calls made on this computer
DEMO_DIR = ROOT / "demo_calls"  # calls shipped with the repo
WEB_DIR = ROOT / "web"
