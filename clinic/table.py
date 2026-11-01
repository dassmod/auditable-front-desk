"""
The table a replay engine uses to re-run this agent's deterministic steps.

Each name maps to the function that re-derives it and to the key in the
step's outputs that holds its answer. The verifier builds this table. A
trace never chooses what gets run.
"""

from clinic.guards import slot_is_free, within_opening_hours, not_in_past
from clinic.parser import parse_booking, parse_arguments
from clinic.session import (
    pending_after_proposal, pending_after_resolution,
    pending_proposal_matches
)
from clinic.tools import find_free_slots

TABLE = {
    "parse_booking": {"fn": parse_booking, "key": "start"},
    "parse_arguments": {"fn": parse_arguments, "key": "status"},
    "slot_is_free": {"fn": slot_is_free, "key": "decision"},
    "within_opening_hours": {"fn": within_opening_hours, "key": "decision"},
    "not_in_past": {"fn": not_in_past, "key": "decision"},
    "find_free_slots": {"fn": find_free_slots, "key": "slots"},
    "pending_after_proposal": {
        "fn": pending_after_proposal, "key": "pending_start"
    },
    "pending_proposal_matches": {
        "fn": pending_proposal_matches, "key": "decision"
    },
    "pending_after_resolution": {
        "fn": pending_after_resolution, "key": "pending_start"
    }
}
