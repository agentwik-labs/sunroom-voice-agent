"""Rules that shouldn't change by accident. Run with: python3 -m unittest discover tests"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sunroom import agents, calls, storage, test_calls, tools
from sunroom.config import ROOT
from sunroom.routing import QuoteRequest, ServiceTicket, sounds_urgent


class Routing(unittest.TestCase):
    def test_impact_sets_priority(self):
        ticket = ServiceTicket(impact="safety_or_open_to_weather", category="leak", install_age="1-5 years", zip_code="80228").finalize()
        self.assertEqual((ticket.priority, ticket.queue, ticket.response_target), ("P1", "Service – Leak Team", "2 hours"))

    def test_structural_is_never_below_p2(self):
        self.assertEqual(ServiceTicket(impact="usable_needs_fixing", category="structural").finalize().priority, "P2")

    def test_emergency_words_override_a_low_impact(self):
        self.assertEqual(ServiceTicket(impact="usable_needs_fixing", summary="Hole in the roof").finalize().priority, "P1")

    def test_denials_are_not_emergencies(self):
        self.assertFalse(sounds_urgent("Door is sticky. No water coming in."))

    def test_lead_scores(self):
        hot = QuoteRequest(zip_code="80525", homeowner="yes", timeline="within_3_months", budget="50k_80k").finalize()
        self.assertEqual((hot.likelihood_score, hot.lead_score, hot.status), (90, "Hot", "Team to reach out"))
        outside = QuoteRequest(zip_code="82001", homeowner="buying", timeline="exploring", budget="unsure").finalize()
        self.assertEqual((outside.likelihood_score, outside.lead_score), (10, "Nurture"))


class Tools(unittest.TestCase):
    def test_bad_details_are_sent_back_to_ask_again(self):
        self.assertIn("5-digit", tools.contact_problem("8022", "3035550142"))
        self.assertIn("phone number", tools.contact_problem("80228", "303555"))
        self.assertEqual(tools.contact_problem("unknown", "unknown"), "")

    def test_phone_numbers_are_cleaned(self):
        self.assertEqual(tools.clean_phone("+1 (303) 555-0142"), "3035550142")

    def test_handoff_switches_agent_and_ticket_saves_once(self):
        call_id = calls._register("realtime", agents.RECEPTIONIST, None)
        self.assertEqual(calls.run_tool(call_id, "transfer_to_service", "")["handoff"]["label"], "the service agent")
        self.assertIn("Still needed", calls.run_tool(call_id, "create_service_ticket", "{}")["output"])
        fields = dict(
            contact_name="Pat Doe", phone="303 555 0142", job_number_or_address="JOB-1", zip_code="80228", install_age="1-5 years",
            category="leak", summary="Water at the ridge", impact="safety_or_open_to_weather", callback_window="today",
        )
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(storage, "RECORDS_DIR", Path(folder)):
            self.assertIn("Priority P1", calls.run_tool(call_id, "create_service_ticket", json.dumps(fields))["output"])
        self.assertEqual(calls._calls[call_id].saves, 1)

    def test_agent_cannot_use_another_agents_tool(self):
        call_id = calls._register("realtime", agents.RECEPTIONIST, None)
        self.assertIn("isn't available", calls.run_tool(call_id, "create_quote_request", "{}")["output"])


class VoiceModels(unittest.TestCase):
    def test_realtime_tools_leave_out_strict_and_live_tools_keep_it(self):
        for agent in (agents.RECEPTIONIST, agents.SERVICE, agents.QUOTE):
            self.assertTrue(all("strict" not in tool for tool in agent.describe()["tools"]))
        self.assertTrue(all(tool["strict"] is False for tool in tools.schemas_for(agents.LIVE.tools)))


class TestCalls(unittest.TestCase):
    def test_accuracy_ignores_fillers_and_punctuation(self):
        self.assertEqual(test_calls.transcription_accuracy(["Uh, 80525."], [{"role": "user", "text": "80525"}]), 100)


class DemoCalls(unittest.TestCase):
    def test_every_demo_call_has_a_recording_and_transcript(self):
        with mock.patch.object(storage, "_FOLDERS", (ROOT / "demo_calls",)):
            items = storage.load_all()
        self.assertTrue(items)
        for item in items:
            if "_call" in item and item["_call"].get("has_audio"):
                self.assertTrue((ROOT / "demo_calls" / "calls" / f"{item['_call']['call_id']}.webm").exists())

    def test_no_api_keys_in_the_repo(self):
        for path in ROOT.rglob("*"):
            if path.is_file() and path.suffix in {".json", ".py", ".js", ".html", ".md", ".example"}:
                self.assertNotRegex(path.read_text(errors="ignore"), r"sk-[A-Za-z0-9_-]{20,}", path)


if __name__ == "__main__":
    unittest.main()
