"""The tools the voice agents can call, as OpenAI schemas and the code behind them."""
from __future__ import annotations

from dataclasses import dataclass, field

from . import storage
from .routing import CATEGORIES, IMPACT_TO_PRIORITY, QuoteRequest, ServiceTicket, in_colorado

SAVE_TOOLS = {"create_service_ticket", "create_quote_request"}


@dataclass
class CallData:
    """What's been captured on one call."""

    ticket: ServiceTicket = field(default_factory=ServiceTicket)
    quote: QuoteRequest = field(default_factory=QuoteRequest)

    def saved_record(self) -> ServiceTicket | QuoteRequest | None:
        if self.ticket.ticket_id:
            return self.ticket
        return self.quote if self.quote.quote_id else None


def _schema(name: str, description: str, required: dict | None = None, optional: dict | None = None) -> dict:
    required, optional = required or {}, optional or {}
    properties = {key: {"type": "string", "description": text} for key, text in {**required, **optional}.items()}
    if "features" in properties:
        properties["features"] = {"type": "array", "items": {"type": "string"}, "description": properties["features"]["description"]}
    return {
        "type": "function",
        "name": name,
        "description": description,
        "strict": False,
        "parameters": {"type": "object", "properties": properties, "required": list(required)},
    }


_SCHEMAS = {
    schema["name"]: schema
    for schema in (
        _schema("end_call", "Ends the call. Use only once the caller has clearly said they're finished."),
        _schema("transfer_to_service", "Use when the caller already has a sunroom from us and has a problem, damage, warranty or billing question."),
        _schema("transfer_to_quote", "Use when the caller is interested in a new sunroom, patio cover, screen room or a quote."),
        _schema("check_service_area", "Check whether a ZIP code is in our Colorado service area.", {"zip_code": "5-digit ZIP code"}),
        _schema(
            "create_service_ticket",
            "Create and route the service ticket once all details are collected.",
            {
                "contact_name": "Caller's full name",
                "phone": "Callback phone number",
                "job_number_or_address": "Job number, or the install address if they don't have it",
                "zip_code": "5-digit ZIP where the sunroom is",
                "install_age": 'One of "<1 year", "1-5 years", "5-10 years", "10+ years", "unknown"',
                "category": f"One of {', '.join(CATEGORIES)}",
                "summary": "One-sentence description of the problem",
                "impact": (
                    "safety_or_open_to_weather for anything unsafe, a hole, missing glass or water or weather getting in right now; "
                    "room_unusable_or_damage_worsening if they can't use the room or it's getting worse; "
                    "usable_needs_fixing if it works but needs repair; question_or_request if nothing is damaged. "
                    "If in doubt, pick the more urgent one."
                ),
                "callback_window": "Best time to call back",
            },
            {
                "email": "Email address, if offered",
                "started": "When it started, if mentioned",
                "details": "Any extra detail",
                "insurance_claim": "For storm damage: filed, planning, no, or unsure",
                "photos": "Whether they can send photos: text_link, email, or none",
            },
        ),
        _schema(
            "create_quote_request",
            "Save the new-sunroom lead so the team can reach out, once all details are collected.",
            {
                "contact_name": "Full name",
                "phone": "Phone number",
                "zip_code": "Project ZIP",
                "homeowner": "yes, no, or buying",
                "room_type": "four_season, three_season, screen_room, patio_cover, solarium, or unsure",
                "building_onto": "deck, patio, new_foundation, replace_existing, or unsure",
                "approx_size": 'Rough size in the caller\'s words, e.g. "about 12 by 20"',
                "timeline": "asap, within_3_months, 3_6_months, or exploring",
                "budget": "under_25k, 25k_50k, 50k_80k, 80k_plus, or unsure",
            },
            {
                "best_time": "A good time to call them, if given",
                "email": "Email address, if offered",
                "city": "City, if mentioned",
                "main_use": "Main use, e.g. year-round living, hot tub, dining, office, if mentioned",
                "features": "Features wanted, if mentioned",
                "hoa": "yes, no, or unsure",
                "financing_interest": "yes, no, or maybe",
                "street_address": "Street address, if mentioned",
                "heard_about_us": "How they heard about us",
                "notes": "Anything else",
            },
        ),
    )
}


def schemas_for(names: tuple[str, ...]) -> list[dict]:
    return [_SCHEMAS[name] for name in names]


def contact_problem(zip_code: str, phone: str) -> str:
    """What's wrong with a ZIP or phone number as heard, so the agent asks again instead of saving it."""
    if zip_code != "unknown" and not (zip_code.isdigit() and len(zip_code) == 5):
        return f"Not saved. '{zip_code}' isn't a 5-digit ZIP code. Ask the caller to repeat it."
    digits = "".join(c for c in phone if c.isdigit())
    if phone != "unknown" and len(digits) != 10 and not (len(digits) == 11 and digits[0] == "1"):
        return f"Not saved. '{phone}' isn't a full phone number. Ask the caller to repeat it."
    return ""


def clean_phone(phone: str) -> str:
    return "".join(c for c in phone if c.isdigit()).removeprefix("1") or phone


def missing_fields(name: str, arguments: dict) -> list[str]:
    return [key for key in _SCHEMAS[name]["parameters"]["required"] if not arguments.get(key)]


def known_fields(name: str, arguments: dict) -> dict:
    return {key: value for key, value in arguments.items() if key in _SCHEMAS[name]["parameters"]["properties"]}


def check_service_area(zip_code: str, outside_area: str) -> str:
    return "In service area." if in_colorado(zip_code) else outside_area


def create_service_ticket(data: CallData, fields: dict) -> str:
    if problem := contact_problem(fields["zip_code"], fields["phone"]):
        return problem
    if fields["impact"] not in IMPACT_TO_PRIORITY:
        return f"Not saved. impact must be exactly one of: {', '.join(IMPACT_TO_PRIORITY)}."
    ticket = data.ticket
    for key, value in fields.items():
        setattr(ticket, key, value)
    if ticket.category not in CATEGORIES:
        ticket.category = "other"
    ticket.phone = clean_phone(ticket.phone)
    ticket.finalize()
    storage.save_record(ticket)
    return (
        f"Ticket {ticket.ticket_id} created. Priority {ticket.priority}, routed to {ticket.queue}. "
        f"Response target {ticket.response_target}. Warranty: {ticket.warranty}. "
        f"Also notified: {', '.join(ticket.also_notify) or 'nobody else'}."
    )


def create_quote_request(data: CallData, fields: dict) -> str:
    if problem := contact_problem(fields["zip_code"], fields["phone"]):
        return problem
    quote = data.quote
    for key, value in fields.items():
        setattr(quote, key, value)
    quote.phone = clean_phone(quote.phone)
    quote.finalize()
    storage.save_record(quote)
    return f"Saved. Reference {quote.quote_id}. Status: {quote.status}. (Internal lead score {quote.lead_score}; don't mention it.)"
