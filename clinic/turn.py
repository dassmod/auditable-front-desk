"""One patient turn on a Session."""

import json
import os

from clinic.tools import TOOLS, find_free_slots
from clinic.parser import parse_arguments
from clinic.guards import slot_is_free, within_opening_hours, not_in_past
from clinic.session import NOW


model_name = os.environ.get("MODEL_NAME")

def run_turn(session, text):
    """Run one patient turn on `session` and return the agent's reply.

    The patient's message goes into the trace and into `session.messages`.
    Then the model is called in a loop. A tool call is answered and the model
    is called again: `find_free_slots` is run as a read, and `book_appointment`
    goes through `parse_arguments`, the three guards and, if all allow, the
    effect. Each answer goes back as a `tool` message. A reply with words ends
    the turn: it is recorded, appended and returned.

    Nothing here saves the trace, and nothing caps the number of tool calls.
    """
    session.recorder.record(
        "nondeterministic", "user_message", {}, {"text": text}
    )
    session.messages.append({"role": "user", "content": text})

    while True:
        response = session.client.chat.completions.create(
            model=model_name,
            messages=session.messages,
            tools=TOOLS
        )

        message = response.choices[0].message

        if message.tool_calls is not None:
            tool_call = message.tool_calls[0]

            # The tool's name picks the code that runs. `find_free_slots` is
            # a read. Any other tool is `book_appointment`, a proposal.
            if tool_call.function.name == "find_free_slots":
                day = json.loads(tool_call.function.arguments)["day"]
                slots = find_free_slots(day, session.booked)
                session.recorder.record(
                    "deterministic",
                    "find_free_slots",
                    {"day": day, "booked": session.booked},
                    {"slots": slots}
                )
                result = json.dumps(slots)
            else:
                status = parse_arguments(tool_call.function.arguments)
                session.recorder.record(
                    "deterministic",
                    "parse_arguments",
                    {"arguments": tool_call.function.arguments},
                    {"status": status}
                )

                if status != "ok":
                    result = status
                else:
                    start = json.loads(tool_call.function.arguments)["start"]

                    # The guards decide. Each is a pure function of its
                    # recorded inputs.
                    is_free = slot_is_free(start, session.booked)
                    session.recorder.record(
                        "deterministic",
                        "slot_is_free",
                        {"start": start, "booked": session.booked},
                        {"decision": is_free}
                    )

                    is_open = within_opening_hours(start)
                    session.recorder.record(
                        "deterministic",
                        "within_opening_hours",
                        {"start": start},
                        {"decision": is_open}
                    )

                    is_in_future = not_in_past(start, NOW)
                    session.recorder.record(
                        "deterministic",
                        "not_in_past",
                        {"start": start, "now": NOW},
                        {"decision": is_in_future}
                    )

                    # The effect acts, only when every guard allows.
                    if (
                        is_free == "allow"
                        and is_open == "allow"
                        and is_in_future == "allow"
                    ):
                        session.booked.append(start)
                        session.recorder.record(
                            "nondeterministic",
                            "book_appointment",
                            {"start": start},
                            {"booked": True}
                        )
                        result = "booked"
                    elif is_free != "allow":
                        result = "refused: not free"
                    elif is_open != "allow":
                        result = "refused: office is not open"
                    elif is_in_future != "allow":
                        result = "refused: requested slot is in past"

            # Answer the call: the model's message, then its tool message,
            # joined to it by id. Then the model is called again.
            session.messages.append(message)
            session.messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })
            continue
        else:
            session.recorder.record(
                "nondeterministic",
                "agent_reply",
                {},
                {"text": message.content}
            )
            session.messages.append({
                "role": "assistant",
                "content": message.content
            })
            return message.content
