"""Live calls: starting them on either voice model, running their tools and saving the result."""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from . import agents, openai_api, prompts, storage, test_calls, tools
from .analysis import analyze_call
from .config import LIVE_BACKEND_MODEL, LIVE_MODEL, REALTIME_MODEL, TRANSCRIPTION_MODEL, TURN_DETECTION, VOICE
from .scenarios import SCENARIOS

ENGINES = {"live": "GPT-Live (talks and listens at once)", "realtime": f"Realtime ({REALTIME_MODEL})"}


@dataclass
class Call:
    engine: str
    agent: agents.Agent
    scenario: str | None
    data: tools.CallData = field(default_factory=tools.CallData)
    saves: int = 0
    finished: bool = False  # set by finish_call; a call is saved and analyzed once
    started: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


_calls: dict[str, Call] = {}  # in memory: calls only need to survive until they end


def _register(engine: str, agent: agents.Agent, scenario: str | None) -> str:
    if scenario and scenario not in SCENARIOS:
        raise ValueError("Unknown test call.")
    call_id = uuid.uuid4().hex
    _calls[call_id] = Call(engine, agent, scenario)
    return call_id


def _get(call_id: str) -> Call:
    if call_id not in _calls:
        raise ValueError("Unknown call. Please start a new one.")
    return _calls[call_id]


def _interrupts(scenario: str | None) -> bool:
    return bool(scenario and SCENARIOS[scenario].get("interrupts"))


def start_realtime_call(scenario: str | None) -> dict:
    """Realtime: the browser connects to OpenAI itself, with a short-lived token from here."""
    agent = agents.RECEPTIONIST
    details = agent.describe()
    reply = openai_api.post("realtime/client_secrets", {
        "session": {
            "type": "realtime",
            "model": REALTIME_MODEL,
            "instructions": details["instructions"],
            "tools": details["tools"],
            "audio": {
                "input": {
                    "transcription": {"model": TRANSCRIPTION_MODEL, "prompt": prompts.TRANSCRIPTION_HINTS},  # no language set, so Spanish works
                    "noise_reduction": {"type": "far_field"},  # laptop mic and speakers, not a headset
                    "turn_detection": {**TURN_DETECTION, "interrupt_response": False},  # the page turns this on after the greeting
                },
                "output": {"voice": VOICE},
            },
        }
    })
    return {
        "engine": "realtime",
        "session_id": _register("realtime", agent, scenario),
        "client_secret": json.loads(reply)["value"],
        "agent": details,
        "turn_detection": TURN_DETECTION,
        "interrupts": _interrupts(scenario),
    }


def start_live_call(scenario: str | None, sdp: str) -> dict:
    """GPT-Live: this server exchanges the browser's offer, so no token reaches the page."""
    agent = agents.LIVE
    reply = openai_api.post("live/sessions", {
        "session": {
            "model": LIVE_MODEL,
            "instructions": agent.instructions,
            "input": [{"role": "developer", "content": [{"type": "input_text", "text": agent.greeting}]}],
            "audio": {"output": {"voice": VOICE}},
            "delegation": {
                "type": "responses",
                "responses": {
                    "model": LIVE_BACKEND_MODEL,
                    "instructions": agent.backend,
                    "tools": tools.schemas_for(agent.tools),
                    "tool_choice": "auto",
                    "parallel_tool_calls": False,
                },
            },
        },
        "transport": {"type": "webrtc", "sdp": sdp},
    })
    return {
        "engine": "live",
        "session_id": _register("live", agent, scenario),
        "answer_sdp": json.loads(reply)["transport"]["sdp"],
        "greeting": agent.greeting,
        "interrupts": _interrupts(scenario),
    }


def run_tool(call_id: str, name: str, arguments: str) -> dict:
    call = _get(call_id)
    if call.finished:
        return {"output": "The call has already ended."}
    if name not in call.agent.tools:
        return {"output": f"{name} isn't available right now."}
    try:
        args = tools.known_fields(name, json.loads(arguments or "{}"))
    except json.JSONDecodeError:
        return {"output": "That didn't work. Collect the details and try again."}
    if missing := tools.missing_fields(name, args):
        return {"output": f"Not saved. Still needed: {', '.join(missing)}."}
    if name in agents.HANDOFFS:
        call.agent = agents.HANDOFFS[name]
        return {"output": "Transferred.", "handoff": call.agent.describe()}
    if name == "check_service_area":
        return {"output": tools.check_service_area(args["zip_code"], call.agent.outside_area)}
    if name == "create_service_ticket":
        output = tools.create_service_ticket(call.data, args)
    elif name == "create_quote_request":
        output = tools.create_quote_request(call.data, args)
    else:
        return {"output": "Ending the call."}
    if not output.startswith("Not saved"):
        call.saves += 1
    return {"output": output}


def next_test_line(call_id: str, transcript: list[dict]) -> dict:
    return test_calls.next_caller_line(_get(call_id).scenario, transcript)


def save_recording(call_id: str, audio: bytes) -> None:
    _get(call_id)  # known call ids only, which also keeps the filename safe
    storage.save_audio(call_id, audio)


def finish_call(call_id: str, transcript: list[dict], duration: float, interruptions: int, spoken: list[str], reply_gaps: list[float]) -> dict:
    call = _get(call_id)
    if call.finished:
        raise ValueError("This call has already ended and been saved.")
    call.finished = True
    saved = call.data.saved_record()
    record = asdict(saved) if saved else None
    meta = {
        "call_id": call_id,
        "started": call.started,
        "duration": duration,
        "engine": call.engine,
        "reply_gaps": reply_gaps,
        "transcript": transcript,
        "record_id": (record or {}).get("ticket_id") or (record or {}).get("quote_id"),
        "has_audio": storage.has_audio(call_id),
    }
    try:
        meta["analysis"] = analyze_call(transcript, record)
    except (ValueError, KeyError) as err:
        meta["analysis_error"] = str(err)  # the call and recording still save
    if call.scenario:
        meta["test"] = test_calls.grade(call.scenario, record, transcript, {
            "saves": call.saves,
            "interruptions": interruptions,
            "spoken": spoken,
            "analysis": meta.get("analysis"),
        })
    storage.save_call(meta)
    return meta
