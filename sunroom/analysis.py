"""The after-call read: needs, wants, result, sentiment and likelihood of purchase."""
from __future__ import annotations

import json

from . import openai_api, prompts
from .config import ANALYSIS_MODEL

_MOODS = ["Positive", "Neutral", "Mixed", "Frustrated", "Angry"]
_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["summary", "needs", "wants", "result", "sentiment", "purchase", "next_action"],
    "properties": {
        "summary": {"type": "string", "description": "Two sentences at most on what the call was about and how it ended."},
        "needs": {"type": "string", "description": "Under 12 words: the underlying problem or requirement, e.g. 'Hole in sunroom roof repaired before more rain gets in'."},
        "wants": {"type": "string", "description": "Under 12 words: what the caller directly asked for, e.g. 'A call back as soon as possible'."},
        "result": {"type": "string", "description": "Under 12 words: what actually happened by the end, including any ticket or reference number. Say so plainly if the call ended with nothing saved."},
        "sentiment": {
            "type": "object",
            "additionalProperties": False,
            "required": ["label", "score", "start", "end", "reason", "quote"],
            "properties": {
                "label": {"type": "string", "enum": _MOODS},
                "score": {"type": "integer", "description": "0 is very negative, 50 neutral, 100 very positive."},
                "start": {"type": "string", "enum": _MOODS},
                "end": {"type": "string", "enum": _MOODS},
                "reason": {"type": "string", "description": "One sentence."},
                "quote": {"type": "string", "description": "The caller's most telling words, copied exactly. Empty if none."},
            },
        },
        "purchase": {
            "type": "object",
            "additionalProperties": False,
            "required": ["applies", "likelihood", "reason", "positive_signals", "risks"],
            "properties": {
                "applies": {"type": "boolean", "description": "True only if the caller showed interest in buying something new."},
                "likelihood": {"type": "integer", "description": "0 to 100 chance they go on to buy. 0 if applies is false."},
                "reason": {"type": "string", "description": "One sentence."},
                "positive_signals": {"type": "array", "items": {"type": "string"}, "description": "Short phrases, at most three."},
                "risks": {"type": "array", "items": {"type": "string"}, "description": "Short phrases, at most three."},
            },
        },
        "next_action": {"type": "string", "description": "The one thing the team should do next."},
    },
}


def analyze_call(transcript: list[dict], record: dict | None) -> dict:
    spoken = [line for line in transcript if line["role"] in ("user", "assistant")]
    lines = "\n".join(f"{'Caller' if line['role'] == 'user' else 'Assistant'}: {line['text']}" for line in spoken)
    fields = {key: value for key, value in (record or {}).items() if value not in ("", [], None) and key != "score_factors"}
    reply = openai_api.post("chat/completions", {
        "model": ANALYSIS_MODEL,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": prompts.ANALYSIS},
            {"role": "user", "content": f"Transcript:\n{lines or '(nothing said)'}\n\nSaved record:\n{json.dumps(fields)}"},
        ],
        "response_format": {"type": "json_schema", "json_schema": {"name": "call_analysis", "strict": True, "schema": _SCHEMA}},
    })
    analysis = json.loads(json.loads(reply)["choices"][0]["message"]["content"])
    # Keep only quotes the caller really said.
    said = " ".join(line["text"] for line in spoken if line["role"] == "user").lower()
    if analysis["sentiment"]["quote"].lower() not in said:
        analysis["sentiment"]["quote"] = ""
    return analysis
