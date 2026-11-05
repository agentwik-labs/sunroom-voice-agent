# Demo guide

Scripts for showing the voice agent live. A full demo is about 8 minutes: Scripts 1 and 4, plus one or two curveballs.

The agent is live AI, so its wording changes every call. The **priority, team and lead score** in each script should match as long as the caller gives those answers. Ticket numbers will differ.

## Before the demo

1. Run `python3 server.py` and open **http://127.0.0.1:8770**.
2. Press **Start call** and allow the microphone, once for practice.
3. Use headphones if you can, or keep the room quiet. Speaker echo or room noise can cut the agent off.
4. Check your internet is reliable. A live call can't survive a real outage.

The transcript runs on the left. When the call ends, the analysis, recording and saved record appear on the right, which is the payoff of the demo.

## What the agent does

- Asks one question at a time and keeps turns short.
- Reads back ZIP codes and phone numbers, and asks people to spell names it's unsure of.
- Understands slang, rambling, one-word answers and Spanish, and lets the latest correction win.
- Says it's a virtual assistant if asked, and says the call is recorded.
- Never quotes prices, or promises warranty coverage, insurance outcomes or repair dates.
- Offers a call back if someone asks for a person, because there's no live transfer.
- Saves what it has if an urgent caller won't stay.

| How bad is it? | Priority | Response target |
|---|---|---|
| Unsafe or open to the weather | P1 | 2 hours |
| Room unusable or damage getting worse | P2 | Same business day |
| Usable, but needs fixing | P3 | 2 business days |
| Just a question | P4 | 3 business days |

Structural problems are never lower than P2.

## Script 1: Leak during a storm (start here)

**Shows:** empathy, urgency, safety advice, top-priority routing.

> **You:** Hi, you built our sunroom a few years ago and water is coming in right now.
> *Name?* **Maria Lopez.**
> *Address?* **1420 Pine Street, Lakewood, 80228.**
> *How bad is it?* **It's dripping on the floor and it's raining hard.**
> *Best number?* **303 555 0142, as soon as possible.**

**Expect:** **P1**, Service – Leak Team, 2 hours.

## Script 2: Hail damage with an insurance claim

> **You:** We got hit by that hailstorm and it cracked some of the roof panels on our sunroom.
> *Name?* **James Carter.**
> *Job number or address?* **JOB-21877.**
> *ZIP?* **80123.**
> *How bad is it?* **We can't use the room, and it's getting worse.**
> *When was it installed?* **Around seven years ago.**
> *Filed a claim?* **Yes, last week.**
> *Best number and time?* **303 555 0142, weekday mornings.**

**Expect:** **P2**, Storm Damage & Claims, same business day, insurance coordinator notified.

**Try asking:** "So will insurance cover all of this?" It shouldn't promise anything.

## Script 3: Sagging roof that seems minor

> **You:** It's probably nothing, but the roof of our sunroom looks like it's sagging a bit. We can still use the room fine.
> *Name?* **Dana Kim.**
> *Address?* **88 Main Street, Longmont, 80501.**
> *When was it installed?* **Over ten years ago.**
> *Best number and time?* **303 555 0142, any afternoon.**

**Expect:** **P2** rather than P3, Service – Structural. The caller played it down, but structural problems are never ranked below P2.

## Script 4: Ready-to-buy lead (start here for sales)

**Shows:** natural intake, the promise to reach out, and the after-call analysis.

> **You:** Hi, I'm thinking about adding a sunroom to my house.
> *Name?* **Alex Rivera.**
> *ZIP?* **80525.**
> *Own the home?* **Yes.**
> *What type of room?* **A four-season room we can use all year.**
> *Built onto what?* **Our existing deck.**
> *How big?* **Maybe 12 by 20.**
> *Timeline?* **In the next couple of months.**
> *Budget?* **Probably 50 to 80 thousand.**
> *Best number and time?* **303 555 0142, afternoons.**

**Expect:** A QTE reference number and a promise that the team will reach out. The page shows lead score **90/100, Hot**, and a high likelihood of purchase. The agent shouldn't say the score out loud, so point it out on the page.

**Try asking:** "What's something like that going to cost?" It shouldn't give a price. "Can I book a time?" It should say the team will set that up.

## Script 5: Caller outside Colorado

> **You:** Hi, I'm looking at getting a sunroom.
> *Name?* **Chris Young.**
> *ZIP?* **82001.** *(Cheyenne, Wyoming)*
> *(offers a referral)* **Sure, that'd be great.**
> *Own the home?* **We're buying one now.**
> *Other questions:* **Four-season room, on a deck, 12 by 20. Just exploring, not sure on budget. My number is 303 555 0142.**

**Expect:** Lead score **10/100, Nurture**, Outside Colorado, and a low likelihood of purchase.

## Curveballs

| Say this | It should |
|---|---|
| *(talk over the agent mid-sentence)* | Stop and respond to you. This best shows it's real-time. |
| "Are you a real person?" | Say it's a virtual assistant |
| "Can I talk to someone?" | Offer a call back and carry on |
| "Actually my ZIP is 80301." | Use the new answer without fuss |
| "I've got a sun porch that's all tore up." | Understand the slang |
| "Hold on a sec." | Say take your time and wait |
| "Ok that's everything, bye." | Say goodbye and hang up |

## If something goes wrong

| What happens | What to do |
|---|---|
| Page won't load | Run `python3 server.py` |
| "Microphone blocked" | Allow the mic from the icon in the address bar. On a Mac, also check System Settings → Privacy & Security → Microphone. |
| Error mentioning the key or OpenAI | Check your key has credit and access to the model, or switch **Voice model** |
| Agent keeps cutting itself off | Use headphones |
| Connection dropped | Check the internet, press **Start call** again, or try another browser |
| Nothing appears on the right | The record saves near the end, so finish the conversation |
| Mic won't work at all | Type your answers in the box under the transcript once connected |

## What to be upfront about

This is a proof of concept. Nothing goes to a CRM, no one is actually notified, and the scores are estimates that haven't been checked against real sales.
