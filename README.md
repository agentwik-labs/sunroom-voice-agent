# Sunroom Voice Agent

A real-time voice agent for a Colorado sunroom company, running in your browser. It answers like a phone receptionist and handles two kinds of call:

1. **Existing customer with a problem:** gathers the details, sets a priority (P1–P4) and response time, routes it to the right team, and creates a service ticket.
2. **Someone interested in a new sunroom:** captures the project details, checks the Colorado service area, scores the lead, and says the team will reach out. It doesn't book appointments.

Every call is recorded and shows up in one table with what the caller **needs**, **wants** and the **result**, plus sentiment and likelihood of purchase. Open any call to replay it, read the transcript and see the saved JSON.

It's a proof of concept. Nothing goes to a CRM, no one is actually notified, and tickets are saved as local files.

The demo calls use simulated callers with synthetic voices, and their names, addresses and phone numbers are made up. "Front Range Sunrooms" is a placeholder name, which you can change with `COMPANY_NAME` in `.env`.

## Quick start

You need Python 3.9 or newer and a browser such as Chrome or Brave. There's nothing to install.

```bash
python3 server.py
```

Open **http://127.0.0.1:8770**. The demo calls are already there, with their recordings and transcripts, and you can browse them without a key.

To make your own calls, paste your [OpenAI API key](https://platform.openai.com/api-keys) into the page. It stays in memory until the server stops. To avoid re-entering it:

```bash
cp .env.example .env    # then add your key to .env
```

Your key stays on your computer: `.env` is ignored by git, and the page never receives it.

## Using it

- **Talk to it:** press **Start call**, allow your microphone and talk as if you'd phoned the company. Try "I'd like a new sunroom" or "My sunroom is leaking". Headphones help, because speaker echo can cut the agent off.
- **Run a test call:** pick one under **Run test call**. A simulated caller speaks to the agent with no mic needed, and the page shows pass or fail against the expected result. Start with interruptions, slang, angry customer and quick customer.
- **Compare voice models:** **Voice model** switches between GPT-Live and Realtime. Each recording shows which one it used and how quickly the agent usually replied.
- **Review a call:** click any row in the table. Click a transcript line to jump to that moment in the recording.

[DEMO.md](DEMO.md) has scripts for showing it to people.

The call section carries its phase as `<section id="call" data-phase="…">`: `loading`, `idle`, `starting`, `connected`,
`ending` or `saving`. Styles, browser tests and scripts that drive the page can wait on it instead of reading the status text.
The phases and what each one enables are listed at the top of the call code in `web/app.js`.

### Costs

Calls and test calls use your OpenAI account. GPT-Live costs $0.05 per minute plus the model that saves records, and Realtime is priced by audio tokens. See [OpenAI's pricing](https://openai.com/api/pricing/).

### The two voice models

| | GPT-Live (`gpt-live-1`) | Realtime (`gpt-realtime-2.1`) |
|---|---|---|
| **Conversation** | Listens and speaks at once, with "mm-hm"s | Takes turns |
| **Saving records** | Hands off to a backend model | Runs tools directly |
| **Agents** | One voice for the whole call | Receptionist hands off to service or new projects |

Your account needs access to whichever model you pick.

## How it works

```
Browser ── audio over WebRTC ──► OpenAI voice model
   │                                    │
   │ ◄──── tool calls and transcripts ──┘
   ▼
server.py ── runs tools, saves records, analyzes the call
```

Audio goes directly between the browser and OpenAI. The local server keeps your key private, runs the tools, and saves each call.

```
server.py               Web server and API routes
sunroom/
  prompts.py            What the agents are told
  agents.py             Each agent's prompt and tools
  tools.py              Tool schemas and the code behind them
  routing.py            Priorities, teams, response times and lead scores
  calls.py              Starting calls, running tools, saving results
  analysis.py           Needs, wants, result, sentiment and purchase likelihood
  scenarios.py          Test call personas and expected results
  test_calls.py         The simulated caller and grading
  storage.py            Reading and writing call files
  openai_api.py         OpenAI requests and the API key
  config.py             Settings
web/                    The page
demo_calls/             Calls shipped with the repo
records/                Calls you make (created on first use, ignored by git)
tests/                  Run with: python3 -m unittest discover tests
```

## Changing things

| To change | Edit |
|---|---|
| Questions and tone | `sunroom/prompts.py` |
| Teams, priorities, response times, lead scoring | `sunroom/routing.py` |
| Test calls | `sunroom/scenarios.py` |
| Fields saved on a ticket or lead | `sunroom/routing.py` and `sunroom/tools.py` |
| Company name, default model, voice, port | `.env` (see `.env.example`) |

To clear calls you've made, delete the `records/` folder. To remove the demo calls, delete `demo_calls/`.

## Good to know

- **Likelihood of purchase and sentiment** are AI estimates from the transcript. They can't hear tone of voice and haven't been checked against real sales.
- **The lead score** is a separate fixed points rule, so the two numbers can differ.
- **Test call voices** are synthetic and clearer than real people, so try it with real callers too.
- **It runs on one computer.** To share it online you'd need to host it and add sign-in, because anyone reaching the server could spend your OpenAI credit.
- **Recordings hold whatever callers say,** including names and phone numbers. Callers are told the call is recorded, but check the rules that apply before using it with real customers.
