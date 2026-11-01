"""Define model-facing tools and the deterministic free-slot lookup.

`find_free_slots` is a read and can be replayed from its recorded inputs.
`book_appointment` proposes a slot; `confirm_appointment` and
`decline_proposal` express the model's interpretation of the patient's reply.
The API handles these proposals and signals in `clinic/turn.py`. The separate
terminal agent in `clinic/agent.py` still has its own booking flow.
"""

from datetime import datetime, timedelta

from clinic.guards import slot_is_free, within_opening_hours
from clinic.world import SLOT_MINUTES, OPEN_TIME

# OpenAI-compatible function tool schemas. `book_appointment` takes `start`,
# `find_free_slots` takes `day`, and confirmation/decline tools take no args.
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": (
                "Propose an appointment slot the patient has requested; this does not book it."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "start": {
                        "type": "string",
                        "description": (
                            "start of the slot in the format is "
                            "2026-10-13T15:00"
                        )
                    }
                },
                "required": ["start"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_free_slots",
            "description": (
                "Use this tool to list the free appointment times "
                "on one day. Call it when the patient asks "
                "what is available or has not chosen a time."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "day": {
                        "type": "string",
                        "description": (
                            "The day to look at, in the format "
                            "2026-10-13."
                        )
                    }
                },
                "required": ["day"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "confirm_appointment",
            "description": (
                "Confirm the currently pending appointment proposal. "
                "Call this only when the patient clearly accepts that specific "
                "appointment, including natural replies such as 'yes', 'that works', "
                "'sure', or 'go ahead'. Do not call it for a rejection, an unclear "
                "reply, or a request to change the date or time. This tool takes no "
                "arguments; the application uses the pending appointment time."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "decline_proposal",
            "description": (
                "Record that the patient has declined the currently proposed "
                "appointment. Call this when the patient clearly rejects that "
                "specific proposal, including natural replies such as 'no', "
                "'that won't work', or 'I don't want that time'. Do not call it "
                "for an unclear reply or a request to change the date or time; "
                "for a requested change, use book_appointment to propose the "
                "new slot. This tool takes no arguments."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]


def find_free_slots(day, booked):
    """
    Return the free slots on `day` (like "2026-10-06") as ISO start times,
    in time order. A slot is free if it is within opening hours and not in
    `booked`.

    The loop walks every slot of the calendar day and the guards cut the ones
    outside opening hours. `booked` is an argument, so the same `day` and
    `booked` always give the same answer. It does not take `now`, so slots in
    the past are listed too.
    """
    # Start at the first slot of the day.
    slot = datetime.fromisoformat(f"{day}T{OPEN_TIME}")
    result = []

    # The loop ends when `slot` rolls over into the next day.
    while day == slot.strftime("%Y-%m-%d"):
        start = slot.strftime("%Y-%m-%dT%H:%M")

        is_free = slot_is_free(start, booked)
        is_open = within_opening_hours(start)

        if is_free == "allow" and is_open == "allow":
            result.append(start)

        # Move on every pass, allowed or not. Inside the `if`, a denied slot
        # would repeat forever.
        slot = slot + timedelta(minutes=SLOT_MINUTES)

    return result
