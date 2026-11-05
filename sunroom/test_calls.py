"""Test calls: the simulated caller's lines, and grading the result against what's expected."""
from __future__ import annotations

import base64
import json
import re
from difflib import SequenceMatcher

from . import openai_api, prompts
from .config import TEST_CALLER_MODEL, TEST_CALLER_VOICE_MODEL
from .scenarios import SCENARIOS

MIN_TRANSCRIPTION_ACCURACY = 90
_DEFAULT_STYLE = "Answer only what was just asked, in a few words."


def next_caller_line(scenario_id: str, transcript: list[dict]) -> dict:
    """The simulated caller's next line, as text and speech."""
    scenario = SCENARIOS[scenario_id]
    persona = " ".join((
        scenario["caller"],
        "You are on the phone with a sunroom company's assistant.",
        scenario.get("style", _DEFAULT_STYLE),
        prompts.TEST_CALLER_MANNER,
    ))
    history = [
        {"role": "user" if line["role"] == "assistant" else "assistant", "content": line["text"]}
        for line in transcript
        if line["role"] in ("assistant", "user")
    ]
    reply = openai_api.post("chat/completions", {
        "model": TEST_CALLER_MODEL,
        "messages": [{"role": "system", "content": persona}, *history],
    })
    line = json.loads(reply)["choices"][0]["message"]["content"].strip()
    speech = openai_api.post("audio/speech", {
        "model": TEST_CALLER_VOICE_MODEL,
        "voice": scenario.get("voice", "ash"),
        "instructions": scenario.get("delivery", "Speak naturally, like someone on the phone."),
        "input": line,
        "response_format": "mp3",
    })
    return {"line": line, "audio": base64.b64encode(speech).decode()}


def transcription_accuracy(spoken: list[str], transcript: list[dict]) -> int:
    """How closely the live transcript matches what the simulated caller actually said."""

    def simplify(text: str) -> str:
        return re.sub(r"[^a-z0-9]", "", re.sub(r"\b(um+|uh+|er+|hmm+|mm+)\b", "", text.lower()))

    said = simplify(" ".join(spoken))
    heard = simplify(" ".join(line["text"] for line in transcript if line["role"] == "user"))
    return round(100 * SequenceMatcher(None, said, heard, autojunk=False).ratio())


def grade(scenario_id: str, record: dict | None, transcript: list[dict], outcome: dict) -> dict:
    """Compare a test call with what its scenario expects. outcome has saves, interruptions, spoken and analysis."""
    scenario = SCENARIOS[scenario_id]
    analysis = outcome.get("analysis") or {}
    sentiment, purchase = analysis.get("sentiment", {}), analysis.get("purchase", {})
    first_words = next((line["text"] for line in transcript if line["role"] == "assistant"), "")
    checks = [
        (key.replace("_", " ").capitalize(), want, (record or {}).get(key, "nothing saved"))
        for key, want in scenario["expect"].items()
    ]
    checks += [("Saved exactly once", 1, outcome["saves"]), ("Said the call is recorded", True, "record" in first_words.lower())]
    limits = scenario.get("analysis", {})
    if "sentiment_below" in limits:
        checks.append((f"Sentiment below {limits['sentiment_below']}", True, sentiment.get("score", 100) < limits["sentiment_below"]))
    if "purchase_above" in limits:
        checks.append((f"Purchase likelihood above {limits['purchase_above']}", True, purchase.get("likelihood", 0) > limits["purchase_above"]))
    if "purchase_below" in limits:
        checks.append((f"Purchase likelihood below {limits['purchase_below']}", True, purchase.get("likelihood", 100) < limits["purchase_below"]))
    if limits.get("not_buying"):
        checks.append(("Not treated as a sale", True, purchase.get("applies") is False))
    if scenario.get("interrupts"):
        checks.append(("Stopped talking when interrupted", True, outcome["interruptions"] > 0))
    results = [{"name": name, "expected": want, "actual": got, "passed": got == want} for name, want, got in checks]
    accuracy = transcription_accuracy(outcome["spoken"], transcript)
    results.append({
        "name": "Transcription accuracy",
        "expected": f"{MIN_TRANSCRIPTION_ACCURACY}% or more",
        "actual": f"{accuracy}%",
        "passed": accuracy >= MIN_TRANSCRIPTION_ACCURACY,
    })
    return {"scenario": scenario_id, "label": scenario["label"], "passed": all(r["passed"] for r in results), "checks": results}
