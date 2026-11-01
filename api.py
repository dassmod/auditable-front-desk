"""Serve the clinic API and Gradio page from one FastAPI application.

Run locally from the repo folder with `.env` exported first (`clinic/turn.py`
reads `MODEL_NAME` once, at import):

    set -a; source .env; set +a
    uvicorn api:app --reload

Open the Gradio page at http://127.0.0.1:8000/ui and the API docs at /docs.
The API routes start sessions, accept messages, return traces and replay them.
Gradio is mounted at `/ui`, so the same Uvicorn server serves both.

Sessions live in this process's memory, so a restart forgets them.
"""

import os
import uuid

import gradio as gr
from fastapi import FastAPI, HTTPException
from openai import OpenAI
from pydantic import BaseModel
from replay.engine import replay_trace

from clinic.session import Session
from clinic.table import TABLE
from clinic.turn import run_turn
from ui import demo


class MessageIn(BaseModel):
    """The body of one patient message."""

    text: str

class ReplyOut(BaseModel):
    """The agent's reply and the calendar after this turn."""

    reply: str
    booked: list[str]

app = FastAPI()

# One model client, shared by every Session. A missing value stops the server
# at start-up with a KeyError, which is the loud failure on purpose.
client = OpenAI(
    base_url=os.environ["MODEL_BASE_URL"],
    api_key=os.environ["MODEL_API_KEY"]
)

# run_id -> Session. Lost on restart.
SESSIONS = {}

def get_session(session_id):
    """Return the Session for `session_id`, or answer 404 if there is none."""
    session = SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="no such session")
    return session

@app.post("/sessions")
def create_session():
    """Start a conversation: make a Session, keep it, return its id."""
    run_id = uuid.uuid4().hex[:8]
    SESSIONS[run_id] = Session(run_id, client)
    return {"session_id": run_id}

@app.post("/sessions/{session_id}/messages", response_model=ReplyOut)
def send_message(session_id: str, body: MessageIn):
    """Run one patient turn and return the reply and the booked slots."""
    session = get_session(session_id)
    reply = run_turn(session, body.text)
    return ReplyOut(reply=reply, booked=session.booked)

@app.get("/sessions/{session_id}/trace")
def get_trace(session_id: str):
    """Return the trace recorded so far, as plain data."""
    session = get_session(session_id)
    return session.recorder.to_dict()

@app.post("/sessions/{session_id}/verify")
def verify(session_id: str):
    """Replay the trace with the clinic's TABLE: one verdict per step."""
    session = get_session(session_id)
    return replay_trace(session.recorder.to_dict(), TABLE)

app = gr.mount_gradio_app(app, demo, path="/ui")
