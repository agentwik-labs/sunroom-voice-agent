"""Routing, priority and lead-scoring rules, plus the ticket and lead records they fill in."""
from __future__ import annotations

import random
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


# ---------- service tickets ----------
CATEGORIES = {
    "leak": "Service – Leak Team",
    "storm_damage": "Storm Damage & Claims",       # hail, wind, snow load
    "glass_window_door": "Service – Glass & Hardware",
    "structural": "Service – Structural",          # roof sagging, frame, foundation
    "electrical_hvac": "Service – Electrical & HVAC",
    "install_punch_list": "Install Project Manager",
    "warranty_question": "Warranty Desk",
    "billing_financing": "Accounts & Financing",
    "other": "Customer Care",
}
IMPACT_TO_PRIORITY = {
    "safety_or_open_to_weather": "P1",
    "room_unusable_or_damage_worsening": "P2",
    "usable_needs_fixing": "P3",
    "question_or_request": "P4",
}
SLA = {"P1": "2 hours", "P2": "same business day", "P3": "2 business days", "P4": "3 business days"}


# Emergencies must never rank low because the model picked the wrong impact.
URGENT = re.compile(
    r"\bhole\b|open to (the )?(weather|elements)|water (is |keeps )?(coming|pouring|dripping|leaking|blowing)|rain (is )?(coming|pouring|blowing)"
    r"|collaps|caving|sparks?\b|smoke|burning|shatter|fell (in|down)",
    re.IGNORECASE,
)


def sounds_urgent(text: str) -> bool:
    """True if a sentence describes an emergency. Skips denials like "no water coming in"."""
    sentences = re.split(r"[.!?;]+", text)
    return any(URGENT.search(s) and not re.search(r"\b(no|not|isn't|isnt|without|never|none)\b", s, re.I) for s in sentences)


def in_colorado(zip_code: str) -> bool:
    return zip_code.isdigit() and len(zip_code) == 5 and 80001 <= int(zip_code) <= 81658


@dataclass
class ServiceTicket:
    contact_name: str = ""
    phone: str = ""
    email: str = ""
    job_number_or_address: str = ""
    zip_code: str = ""
    install_age: str = ""          # "<1 year", "1-5 years", "5-10 years", "10+ years", "unknown"
    category: str = ""
    summary: str = ""
    details: str = ""
    impact: str = ""
    started: str = ""
    insurance_claim: str = ""
    photos: str = ""
    callback_window: str = ""
    # computed
    ticket_id: str = ""
    priority: str = ""
    queue: str = ""
    also_notify: list[str] = field(default_factory=list)
    response_target: str = ""
    warranty: str = ""
    service_area: str = ""
    status: str = ""
    created: str = ""

    def finalize(self) -> "ServiceTicket":
        p = IMPACT_TO_PRIORITY.get(self.impact, "P3")
        if sounds_urgent(f"{self.summary}. {self.details}"):
            p = "P1"
        if self.category == "structural" and p > "P2":
            p = "P2"  # structural problems never sit below P2
        self.priority = p
        self.queue = CATEGORIES.get(self.category, CATEGORIES["other"])
        self.response_target = SLA[p]
        self.warranty = (
            "Likely in warranty" if self.install_age in ("<1 year", "1-5 years")
            else "Unknown – verify" if self.install_age in ("", "unknown")
            else "Likely out of warranty (billable)"
        )
        notify = []
        if self.warranty.startswith("Likely in"):
            notify.append("Warranty Desk")
        if self.insurance_claim in ("filed", "planning"):
            notify.append("Insurance coordinator")
        if p == "P1":
            notify.append("On-call service manager")
        self.also_notify = notify
        self.service_area = "Colorado – in area" if in_colorado(self.zip_code) else "Outside Colorado – review"
        self.ticket_id = self.ticket_id or f"SVC-{random.randint(100000, 999999)}"
        self.status = "New"
        self.created = datetime.now(timezone.utc).isoformat()
        return self


# ---------- new sunroom leads ----------
@dataclass
class QuoteRequest:
    contact_name: str = ""
    phone: str = ""
    email: str = ""
    zip_code: str = ""
    city: str = ""
    homeowner: str = ""            # "yes", "no", "buying"
    room_type: str = ""            # four_season, three_season, screen_room, patio_cover, solarium, unsure
    building_onto: str = ""        # deck, patio, new_foundation, replace_existing, unsure
    approx_size: str = ""
    main_use: str = ""
    features: list[str] = field(default_factory=list)
    hoa: str = ""
    timeline: str = ""             # asap, within_3_months, 3_6_months, exploring
    budget: str = ""               # under_25k, 25k_50k, 50k_80k, 80k_plus, unsure
    financing_interest: str = ""
    street_address: str = ""
    best_time: str = ""
    heard_about_us: str = ""
    notes: str = ""
    # computed
    quote_id: str = ""
    service_area: str = ""
    lead_score: str = ""
    likelihood_score: int = 0      # 0-100, from the same points as lead_score. A demo rule, not a trained model.
    score_factors: list[dict] = field(default_factory=list)
    status: str = ""
    created: str = ""

    def finalize(self) -> "QuoteRequest":
        self.service_area = "Colorado – in area" if in_colorado(self.zip_code) else "Outside Colorado"
        factors = [
            ("In the Colorado service area", 2 if self.service_area.startswith("Colorado") else 0, 2),
            ("Owns the home", {"yes": 2, "buying": 1}.get(self.homeowner, 0), 2),
            ("Timeline", {"asap": 3, "within_3_months": 2, "3_6_months": 1}.get(self.timeline, 0), 3),
            ("Budget", {"80k_plus": 3, "50k_80k": 3, "25k_50k": 2, "under_25k": 1}.get(self.budget, 0), 3),
        ]
        points = sum(f[1] for f in factors)
        self.score_factors = [{"factor": f, "points": p, "max": m} for f, p, m in factors]
        self.likelihood_score = round(100 * points / sum(f[2] for f in factors))
        self.lead_score = "Hot" if points >= 8 else "Warm" if points >= 5 else "Nurture"
        self.quote_id = self.quote_id or f"QTE-{random.randint(100000, 999999)}"
        self.status = "Team to reach out"
        self.created = datetime.now(timezone.utc).isoformat()
        return self
