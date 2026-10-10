# auditable-front-desk

A receptionist agent for a fictional clinic, built so that every booking it makes leaves a record a stranger can re-check.

The model reads the patient's request and asks for a booking. Plain code decides whether the booking is allowed. Every step is written to a trace as it happens, and [`proof-of-agent-run`](https://github.com/dassmod/proof-of-agent-run) replays the trace afterwards and reports, step by step, what it could confirm.

## What it does not claim

Read this first, because replay sounds stronger than it is.

It does not prove a run was correct, honest, or safe. It proves something narrower: **every decision step recorded in the trace is the answer the clinic's own code gives on the inputs the trace records.**

The inputs themselves are a claim. The trace is written by the agent, the same party whose correctness is in question. If the trace says the calendar held three bookings when it held five, replay confirms the guard answered correctly on the calendar it was shown, and says nothing about the real one. What the model chose to say cannot be replayed at all, and the report says so instead of guessing.

Replay also checks each step on its own. It does not yet check that the steps agree with each other: a trace that records a guard saying `deny` and then a booking anyway would replay with every step reported as `match`.

There is no overall verdict. Each step gets its own answer: it matched, it diverged, or it could not be checked, and why.

## How it works

**The model proposes, the guards decide, the effect acts.**

1. The patient asks in plain language: "Book me in for Sunday at 10am".
2. The model answers with a tool call, `book_appointment`, carrying a start time such as `2026-10-04T10:00`. It never books anything itself.
3. Three guards run on that start time. Each is a pure function that returns `allow` or `deny`:
   - `slot_is_free(start, booked)`: nobody holds that slot already.
   - `within_opening_hours(start)`: the slot is on an open day and ends by closing time.
   - `not_in_past(start, now)`: the slot starts after `now`.
4. Only if all three allow is the booking written. Otherwise the model is told which guard refused, and it tells the patient.
5. The recorder appends each step to the trace the moment it happens, copied through JSON, so a later change to the agent's data cannot rewrite what was recorded.
6. `verify.py` hands the trace and the clinic's table of replayable steps to `proof-of-agent-run`, which re-runs each one and compares.

A guard never reads the clock, the calendar or the network. Anything it needs about the world arrives as an argument and goes into the trace. That is what makes it replayable tomorrow, when the world is different. The table of what may be re-run lives in this repo (`clinic/table.py`), so a trace never chooses what gets executed.

## One run, replayed

Asked for a Sunday, the model proposed `2026-10-04T10:00`. `within_opening_hours` refused it, no booking was written, and the model told the patient the office is closed that day. Replaying that trace:

```
$ python verify.py traces/conv-0003.json
conv-0003
   0  user_message           skipped
   1  model_decision         skipped
   2  slot_is_free           match  recorded=allow rederived=allow
   3  within_opening_hours   match  recorded=deny rederived=deny
   4  not_in_past            match  recorded=allow rederived=allow
   5  agent_reply            skipped
```

`skipped` means the step cannot be re-run: what the patient wrote, what the model chose, what it replied. Edit the recorded `deny` to `allow` and the same command reports `divergence` on step 3 and `match` everywhere else.

## Run it

`proof-of-agent-run` sits next to this repo, and this one imports it.

```
git clone https://github.com/dassmod/proof-of-agent-run
git clone https://github.com/dassmod/auditable-front-desk
cd auditable-front-desk
python3 -m venv .venv && source .venv/bin/activate
pip install -e ../proof-of-agent-run
pip install openai
mkdir -p traces
cp .env.example .env    # fill in the three values
set -a; source .env; set +a
python -m clinic.agent
python verify.py traces/conv-0004.json
```

The model is reached through any OpenAI-compatible chat API: `.env` holds `MODEL_BASE_URL`, `MODEL_API_KEY` and `MODEL_NAME`, and changing provider is a change to those three values, not to the code. Each run handles one request (the user message near the top of `clinic/agent.py`) and saves one trace.

Two ways to run it with no model at all:

```
python -m clinic.scripted    # type "book tuesday 15:00", then "quit"
python test_parser.py        # prints ok
```

`clinic/scripted.py` is the same loop with a small parser in place of the model, so every step in its trace is one you can reason about completely.

## What is in it

```
clinic/world.py      the clinic: opening days and hours, slot length, starting bookings
clinic/guards.py     the three guards, pure functions
clinic/parser.py     turns "book tuesday 15:00" into a start time, for the scripted loop
clinic/table.py      the steps a replay may re-run, and where each one's answer is
clinic/trace.py      the recorder
clinic/scripted.py   the booking loop with no model
clinic/agent.py      the booking loop with a model
verify.py            replays a trace through proof-of-agent-run
WORKLOG.md           one dated entry per session: where it stopped, what is next, what is open
```

## Where it goes

The agent's brain is the same whether it types or talks, so what comes next puts more around it without changing it:

- **A conversation,** not a single request, including asking the patient to confirm a date the model worked out by itself.
- **Forged traces, built on purpose,** to show exactly where replay stops: a guard step left out, an edited calendar, a `deny` followed by a booking.
- **A voice in the browser,** with speech-to-text and text-to-speech served by [Chutes](https://chutes.ai), Bittensor subnet 64.
- **A phone number** to call it on.
- **Other voices and languages** from other Bittensor subnets, including a caller who switches language mid-call.
- **The verdict on chain,** published through the ERC-8004 validation registry on a testnet.

The clinic is fictional. The calendar is fake. No real personal or health information ever enters it.

## Why a clinic

A booking line is deliberately ordinary. A crypto-themed demo would prove something nobody doubts. A front desk tests the question decentralized networks have not answered yet: whether a normal business can run on what they produce, and check what it was given.
