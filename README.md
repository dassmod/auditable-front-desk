# auditable-front-desk

A receptionist agent for a fictional clinic, built so that every booking it makes leaves a record a stranger can re-check.

The project has a FastAPI service and a Gradio chat page. The model interprets a patient's words and proposes tool calls. Python code checks a proposed booking against the calendar, opening hours and demo clock; only then can the booking be added to that session's calendar. The recorder captures the steps, and `proof-of-agent-run` replays the deterministic ones.

This is a learning demo. The clinic and calendar are fictional; do not enter real patient or health information.

## What replay means

Replay makes a narrow claim: for each deterministic step in the trace, the clinic's registered function returns the recorded answer when given the recorded inputs.

Replay does **not** prove that the trace is complete or truthful, that the recorded inputs reflect a real calendar, or that the model's interpretation and wording are correct. The agent writes the trace itself. Replay checks steps one at a time; it does not currently enforce that every booking has all required guard steps or that one step's inputs agree with earlier steps.

The report is per step, not one overall verdict:

- `match`: the registered function returned the recorded answer.
- `divergence`: the function returned a different answer.
- `skipped`: the step is not replayed, such as a patient message, model reply or booking effect.
- Other could-not-check statuses explain why a step could not be replayed, for example when its name is not in the replay table.

The model's words and choices are nondeterministic, so replay skips them rather than pretending to verify them. The replay table in `clinic/table.py` is the whitelist of functions that may be run again.

The files in `examples/` make the boundary concrete:

- `forged-deny-to-allow.json` changes a recorded guard answer; replay reports a divergence for that step.
- `forged-missing-guards.json` removes the guard steps before a booking; replay does not currently report that those steps are missing.
- `forged-booked-list.json` removes a taken slot from the guard's recorded calendar; the guard matches the incomplete calendar it was given.

## How a booking works

1. The patient sends a message in the Gradio page or to the API.
2. The model can ask a follow-up question, look up free slots with `find_free_slots`, or propose a start time with `book_appointment`.
3. A booking proposal is parsed, then checked by `slot_is_free`, `within_opening_hours` and `not_in_past`.
4. The booking is added to that session's calendar only if all three guards allow it.
5. The recorder captures the interaction and deterministic decisions. The Verify button asks the API to replay that session's trace.

## Run with Docker

Docker runs FastAPI and the Gradio page in one container on port `8000`. Docker Desktop (or another running Docker engine) must be installed first.

From the repository folder, create a local `.env` file and fill in the three values for your OpenAI-compatible model provider:

```sh
cp -n .env.example .env
```

The `-n` option leaves an existing `.env` untouched. The required variables are `MODEL_BASE_URL`, `MODEL_API_KEY` and `MODEL_NAME`. Keep `.env` private; it is excluded from the image build by `.dockerignore`.

Build the image:

```sh
docker build -t auditable-front-desk .
```

Start the container:

```sh
docker run --rm --env-file .env -p 8000:8000 auditable-front-desk
```

Open the chat at <http://localhost:8000/ui>. Send a message, then press **Verify** to see the replay verdicts. FastAPI's interactive API documentation is at <http://localhost:8000/docs>.

The container stays attached to the terminal. Press **Ctrl+C** there to stop it. The `--rm` option removes the stopped container; the built image remains on your machine.

If your model provider is running on your Mac rather than at a reachable network address, `localhost` in `MODEL_BASE_URL` points inside the container. With Docker Desktop, use `host.docker.internal` to reach a service running on the Mac host.

## Run locally with Python

From the repository folder:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp -n .env.example .env
```

Fill in the three model settings in `.env`, then export them and start the combined API and UI server:

```sh
set -a
source .env
set +a
uvicorn api:app --reload
```

Visit <http://127.0.0.1:8000/ui> for the chat or <http://127.0.0.1:8000/docs> for the API docs. Stop the local server with **Ctrl+C**.

The standalone Gradio development entry point is also available with `python ui.py`, but it expects the API to already be running at `http://127.0.0.1:8000`. The normal local command above mounts the page into FastAPI, as the Docker container does.

## HTTP API

All routes are served by the same process as the UI:

| Method | Route | Purpose |
| --- | --- | --- |
| `POST` | `/sessions` | Create an in-memory conversation and return its `session_id`. |
| `POST` | `/sessions/{session_id}/messages` | Send `{"text": "..."}` and receive the reply and current booked slots. |
| `GET` | `/sessions/{session_id}/trace` | Return the recorded trace for that conversation. |
| `POST` | `/sessions/{session_id}/verify` | Replay that trace and return one verdict per step. |

The interactive request forms and response schemas are available at `/docs` while the service is running.

## State and limits

- Sessions and their calendars live in server memory. Restarting the server or container loses them.
- API-created traces are returned by the trace route; they are not automatically saved as files.
- The demo clock is fixed at `2026-10-01T09:12` in `clinic/session.py`. Relative dates and the `not_in_past` check use that value, not the computer's current time.
- The API has no authentication and is intended for local demonstration, not public deployment.
- The starting calendar is sample data in `clinic/world.py`; it is not a real booking system.

## Command-line learning versions

The repository also keeps two earlier ways to explore the booking logic from a terminal. They are development entry points and are excluded from the Docker image by `.dockerignore`.

```sh
mkdir -p traces
python -m clinic.scripted
```

At the prompt, try `book tuesday 15:00`, then type `quit` to save the trace. `clinic.scripted` reads simple typed requests without a model. To run the model-backed terminal loop instead, activate the virtual environment, export `.env` as above, then run:

```sh
python -m clinic.agent
```

These loops save traces under `traces/`. The model-backed terminal agent uses the `RUN_ID` constant in `clinic/agent.py` for its filename; change it before another run if you want to keep an existing trace. Replay a saved trace locally with:

```sh
python verify.py traces/conv-0001.json
```

For a trace that is available in a fresh checkout, use one of the examples:

```sh
python verify.py examples/forged-deny-to-allow.json
```

## Repository map

```text
api.py                 FastAPI routes; mounts the Gradio page at /ui
ui.py                  Gradio chat and Verify button
clinic/session.py      per-conversation messages, calendar and recorder
clinic/turn.py         model calls, tool handling, guards and booking effect
clinic/tools.py        model tool definitions and free-slot lookup
clinic/guards.py       pure booking rules
clinic/parser.py       parser for booking arguments and terminal input
clinic/table.py        replay whitelist and output keys
clinic/trace.py        trace recorder and JSON serialization
clinic/world.py        clinic settings, fixed demo data and starting calendar
verify.py              command-line trace replay for local trace files
examples/              forged sample traces illustrating replay's limits
requirements.txt       pinned Python dependencies, including replay engine
Dockerfile             image recipe for the combined API and UI
.dockerignore          files omitted from the container build context
WORKLOG.md             dated learning-session notes and next steps
```

## Project direction

The next planned steps are to make the model confirm a resolved date before booking, and to strengthen replay so it can detect missing or inconsistent steps across a trace. Later directions include voice interaction, a phone entry point, additional voices and languages, and publishing a verdict through a validation registry.

A front desk is deliberately ordinary: it tests whether a business task can be handled by a model and then checked against the inputs and decisions recorded by the application.

## License

MIT. See [LICENSE](LICENSE).
