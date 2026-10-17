"""One conversation as one object: the state that belongs to it."""

from dataclasses import dataclass, field
from clinic.world import BOOKED
from clinic.trace import Recorder


def fresh_calendar():
    """Return a copy of the world's calendar, so each Session owns its own."""
    return list(BOOKED)


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
    messages: list = field(default_factory=list)
    booked: list = field(default_factory=fresh_calendar)
    recorder: Recorder = field(init=False)

    def __post_init__(self):
        self.recorder = Recorder(self.run_id)
