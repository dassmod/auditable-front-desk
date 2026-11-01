"""One conversation as one object: the state that belongs to it."""

from dataclasses import dataclass, field
from datetime import datetime
from textwrap import dedent

from clinic.trace import Recorder
from clinic.world import (
    BOOKED, CLINIC_NAME, SLOT_MINUTES, OPEN_TIME, CLOSE_TIME
)


def fresh_calendar():
    """Return a copy of the world's calendar, so each Session owns its own."""
    return list(BOOKED)


def fresh_messages(timestamp):
    """Build a session's initial model context using its captured timestamp."""
    return [
        {
            "role": "system",
            "content": dedent(f"""\
                You are the front desk assistant for {CLINIC_NAME}, a clinic that books appointments.
                The clinic is open Monday to Friday, from {OPEN_TIME} to {CLOSE_TIME}. Each appointment lasts {SLOT_MINUTES} minutes.
                Today's date and time is {timestamp}. Work out words like "tomorrow" or "next Tuesday" from this date.

                When the patient gives a specific day and time, call book_appointment with start in the format YYYY-MM-DDTHH:MM, for example 2026-10-13T15:00. This proposes a slot; it does not book it. After the application records the proposal, tell the patient the exact date and time and ask whether they want to confirm it.

                When the patient clearly accepts the pending proposal in their own words, call confirm_appointment. Natural confirmations include "yes", "that works", "sure", or "go ahead". Do not call this tool for a rejection, an unclear reply, or a request to change the date or time.

                When the patient clearly rejects the pending proposal, call decline_proposal. Natural rejections include "no", "that won't work", or "I don't want that time". Do not call this tool for an unclear reply or a request to change the date or time.

                When the patient asks for a different date or time, call book_appointment to propose the new slot. If their reply is unclear, ask a follow-up question and leave the pending proposal unchanged.

                Never say an appointment is booked unless confirm_appointment returns "booked". If the application refuses a proposal, confirmation, or decline, explain the reason it returned.
            """)
        }
    ]


def pending_after_proposal(pending_start, proposed_start):
    """Return the pending slot after the model proposes a new one."""
    return proposed_start


def pending_proposal_matches(pending_start, pending_at_turn_start):
    """Return whether the same proposal was pending at turn start."""
    if pending_start is not None and pending_start == pending_at_turn_start:
        return "allow"
    return "deny"


def pending_after_resolution(pending_start, pending_at_turn_start):
    """Clear a proposal resolved this turn; otherwise preserve the state."""
    if pending_proposal_matches(pending_start, pending_at_turn_start) == "allow":
        return None
    return pending_start


@dataclass
class Session:
    """The state that belongs to one API conversation.

    `now` is captured at creation and used to build the initial model prompt.
    `pending_start` holds a proposed slot until the patient confirms or declines
    it. `booked` is a fresh calendar copy. `messages` and `recorder` are built
    in `__post_init__`; `run_id` and `client` are the required fields.
    """

    run_id: str
    client: object  # the model client; a test passes a fake one
    now: str = field(
        default_factory=lambda: datetime.now().isoformat(timespec="minutes")
    )
    pending_start: str | None = None
    messages: list = field(init=False)
    booked: list = field(default_factory=fresh_calendar)
    recorder: Recorder = field(init=False)

    def __post_init__(self):
        """Create this session's recorder and initial model context."""
        self.recorder = Recorder(self.run_id)
        self.messages = fresh_messages(self.now)
