"""One conversation as one object: the state that belongs to it."""

from dataclasses import dataclass, field
from clinic.world import (
    BOOKED, CLINIC_NAME, SLOT_MINUTES, OPEN_TIME, CLOSE_TIME
)
from clinic.trace import Recorder

# The clock is fixed. It is told to the model in the system prompt, passed to
# `not_in_past` and recorded in the trace as an input. `agent.py` keeps its own
# copy of this value.
NOW = "2026-10-01T09:12"

def fresh_calendar():
    """Return a copy of the world's calendar, so each Session owns its own."""
    return list(BOOKED)

def fresh_messages():
    """Return a new message list that holds only the system prompt.

    Each Session calls this once, so no two Sessions share a list. The prompt
    is the same text as the one in `agent.py`.
    """
    return [
        {
            "role": "system",
            "content": f"""You are the front desk assistant for {CLINIC_NAME}, a clinic that books appointments.
The clinic is open Monday to Friday, from {OPEN_TIME} to {CLOSE_TIME}. Each appointment lasts {SLOT_MINUTES} minutes.
Today's date and time is {NOW}. Work out words like "tomorrow" or "next Tuesday" from this date.
When the patient has given a specific day and time, call book_appointment with start in the format YYYY-MM-DDTHH:MM, for example 2026-10-13T15:00.
If the day or time is unclear, ask the patient before calling the tool.
The booking system decides whether a slot is allowed. Never tell the patient an appointment is booked until the tool result says booked, and if it refuses, tell them the reason you were given."""
        }
    ]

@dataclass
class Session:
    """Everything that belongs to one conversation.

    `messages` and `booked` are made new for every Session by a default
    factory, so two Sessions never share a list. `recorder` is built from
    `run_id` in `__post_init__`, after the other fields are set. `client`
    has no default and comes right after `run_id`, because a field with no
    default must come before a field with one.
    """

    run_id: str
    client: object  # the model client; a test passes a fake one
    messages: list = field(default_factory=fresh_messages)
    booked: list = field(default_factory=fresh_calendar)
    recorder: Recorder = field(init=False)

    def __post_init__(self):
        self.recorder = Recorder(self.run_id)
