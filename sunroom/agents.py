"""The voice agents: what each one is told and which tools it can use."""
from __future__ import annotations

from dataclasses import dataclass

from . import prompts
from .tools import schemas_for


@dataclass(frozen=True)
class Agent:
    label: str
    instructions: str
    greeting: str
    tools: tuple[str, ...]
    outside_area: str = prompts.QUOTE_OUTSIDE_AREA
    backend: str = ""  # GPT-Live only: instructions for the model that runs its tools

    def describe(self) -> dict:
        """What the page needs in order to switch the call to this agent."""
        return {
            "label": self.label,
            "instructions": self.instructions,
            "greeting": self.greeting,
            "tools": [{key: value for key, value in schema.items() if key != "strict"} for schema in schemas_for(self.tools)],  # Realtime rejects "strict"
        }


RECEPTIONIST = Agent(
    label="the receptionist",
    instructions=prompts.RECEPTIONIST,
    greeting=prompts.RECEPTIONIST_GREETING,
    tools=("transfer_to_service", "transfer_to_quote", "end_call"),
)
SERVICE = Agent(
    label="the service agent",
    instructions=prompts.SERVICE,
    greeting=prompts.SERVICE_GREETING,
    tools=("check_service_area", "create_service_ticket", "transfer_to_quote", "end_call"),
    outside_area=prompts.SERVICE_OUTSIDE_AREA,
)
QUOTE = Agent(
    label="the new projects agent",
    instructions=prompts.QUOTE,
    greeting=prompts.QUOTE_GREETING,
    tools=("check_service_area", "create_quote_request", "transfer_to_service", "end_call"),
)
# GPT-Live keeps one voice for the whole call, with a backend model running the tools.
LIVE = Agent(
    label="GPT-Live",
    instructions=prompts.LIVE_VOICE,
    greeting=prompts.LIVE_GREETING,
    tools=("check_service_area", "create_service_ticket", "create_quote_request", "end_call"),
    backend=prompts.LIVE_BACKEND,
)
HANDOFFS = {"transfer_to_service": SERVICE, "transfer_to_quote": QUOTE}
