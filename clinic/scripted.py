"""
A scripted booking loop: read a line, parse it, run the guards, book or
refuse, and record every step. Type quit to save the trace.
"""

from datetime import datetime
from clinic.trace import Recorder
from clinic.guards import slot_is_free, within_opening_hours, not_in_past
from clinic.world import OPEN_DAYS, OPEN_TIME, CLOSE_TIME, SLOT_MINUTES, BOOKED
from clinic.parser import parse_booking

NOW = "2026-10-01T09:12"
rec = Recorder("conv-0001")

while True:
    user_message = input("> ")

    if user_message == "quit":
        rec.save("traces/conv-0001.json")
        break

    rec.record("nondeterministic", "user_message", {}, {"text": user_message})
    start = parse_booking(user_message, NOW)
    rec.record("deterministic", "parse_booking", {"text": user_message, "now": NOW}, {"start": start})

    if start is None:
        agent_reply = "did not understand"
        rec.record("nondeterministic", "agent_reply", {}, {"text": agent_reply})
        print(agent_reply)
        continue

    is_free = slot_is_free(start, BOOKED)
    rec.record("deterministic", "slot_is_free",
        {"start": start, "booked": BOOKED}, {"decision": is_free})

    is_open = within_opening_hours(start)
    rec.record("deterministic", "within_opening_hours",
        {"start": start}, {"decision": is_open})

    is_in_future = not_in_past(start, NOW)
    rec.record("deterministic", "not_in_past",
        {"start": start, "now": NOW}, {"decision": is_in_future})

    if is_free == "allow" and is_open == "allow" and is_in_future == "allow":
        BOOKED.append(start)
        rec.record("nondeterministic", "book_appointment",
            {"start": start}, {"booked": True})
        agent_reply = "Booked"
    else:
        agent_reply = "Not booked"
    rec.record("nondeterministic", "agent_reply", {}, {"text": agent_reply})

    print(agent_reply)