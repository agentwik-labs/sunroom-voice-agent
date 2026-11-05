"""Saved tickets, leads, call transcripts and recordings, as files on disk.

    demo_calls/   shipped with the repo, read only
    records/      calls made on this computer, ignored by git

Each folder holds <ticket or lead id>.json in records/, and <call id>.json plus <call id>.webm in calls/.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .config import DEMO_DIR, RECORDS_DIR

_FOLDERS = (DEMO_DIR, RECORDS_DIR)


def _record_id(record: dict) -> str | None:
    return record.get("ticket_id") or record.get("quote_id")


def _read_json_files(folder: Path) -> list[dict]:
    items = []
    for path in folder.glob("*.json"):
        try:
            items.append(json.loads(path.read_text()))
        except (OSError, json.JSONDecodeError):
            continue  # caught mid-write; the next poll picks it up
    return items


def save_record(record) -> None:
    data = asdict(record)
    (RECORDS_DIR / "records").mkdir(parents=True, exist_ok=True)
    (RECORDS_DIR / "records" / f"{_record_id(data)}.json").write_text(json.dumps(data, indent=2))


def save_audio(call_id: str, audio: bytes) -> None:
    (RECORDS_DIR / "calls").mkdir(parents=True, exist_ok=True)
    (RECORDS_DIR / "calls" / f"{call_id}.webm").write_bytes(audio)


def has_audio(call_id: str) -> bool:
    return (RECORDS_DIR / "calls" / f"{call_id}.webm").exists()


def save_call(meta: dict) -> None:
    (RECORDS_DIR / "calls").mkdir(parents=True, exist_ok=True)
    (RECORDS_DIR / "calls" / f"{meta['call_id']}.json").write_text(json.dumps(meta, indent=2))


def find_audio(call_id: str) -> bytes | None:
    for folder in _FOLDERS:
        path = folder / "calls" / f"{call_id}.webm"
        if path.exists():
            return path.read_bytes()
    return None


def load_all() -> list[dict]:
    """Every saved ticket and lead with its call attached, plus calls that ended before saving anything. Newest first."""
    records = {_record_id(r): r for folder in _FOLDERS for r in _read_json_files(folder / "records")}
    items = list(records.values())
    for folder in _FOLDERS:
        for meta in _read_json_files(folder / "calls"):
            record = records.get(meta.get("record_id"))
            if record is not None:
                record["_call"] = meta
            else:
                items.append({"created": meta.get("started", ""), "_call": meta})
    return sorted(items, key=lambda r: r.get("created", ""), reverse=True)
