"""
The tools the model may use. `TOOLS` is the list the model sees.
`find_free_slots` is a read: it returns the free slots of one day and changes
nothing. It is a pure function of its arguments, so a replay engine can re-run
it from a recorded trace. `book_appointment` is not a function here: the model
only proposes it, and the guards and the effect run in clinic/turn.py and
clinic/agent.py.
"""

from datetime import datetime, timedelta

from clinic.guards import slot_is_free, within_opening_hours
from clinic.world import SLOT_MINUTES, OPEN_TIME

# The tool list in the OpenAI function-calling shape. The model reads every
# `description`, so changing a word changes what it does. `book_appointment`
# takes `start`. `find_free_slots` takes `day`.
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": (
                "use this tool when patient wants to book an appointment"
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
