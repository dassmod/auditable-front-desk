"""
The table a replay engine uses to re-run this agent's deterministic steps.

Each name maps to the function that re-derives it and to the key in the
step's outputs that holds its answer. The verifier builds this table. A
trace never chooses what gets run.
"""

from clinic.guards import slot_is_free, within_opening_hours, not_in_past
from clinic.parser import parse_booking

TABLE = {
    "parse_booking": {"fn": parse_booking, "key": "start"},
    "slot_is_free": {"fn": slot_is_free, "key": "decision"},
    "within_opening_hours": {"fn": within_opening_hours, "key": "decision"},
    "not_in_past": {"fn": not_in_past, "key": "decision"},
}
