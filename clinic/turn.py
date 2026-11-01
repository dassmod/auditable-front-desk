"""Run one patient turn, handling slot proposals and confirmations."""

import json
import os

from clinic.guards import slot_is_free, within_opening_hours, not_in_past
from clinic.parser import parse_arguments
from clinic.session import (
    pending_after_proposal, pending_after_resolution,
    pending_proposal_matches
)
from clinic.tools import TOOLS, find_free_slots


model_name = os.environ.get("MODEL_NAME")


def run_turn(session, text):
    """Process one patient message and return the assistant's text reply.

    The model may look up slots, propose a slot, confirm an earlier proposal,
    or decline one. Proposals are held in `session.pending_start`. A confirmation
    can book only a proposal that was pending at the start of this patient turn;
    the booking guards run immediately before the effect. A decline clears that
    pending proposal. Model tool choices, patient messages, assistant replies,
    deterministic checks and successful booking effects are recorded.

    This function keeps the trace in memory and does not limit model tool calls.
    """
    pending_at_turn_start = session.pending_start
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
            session.recorder.record(
                "nondeterministic",
                "model_decision",
                {},
                {
                    "tool_name": tool_call.function.name,
                    "arguments": tool_call.function.arguments
                }
            )

            # Slot lookup is a read; booking proposes a slot; confirmation
            # and decline are model interpretations handled below.
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
            elif tool_call.function.name == "book_appointment":
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
                    before = session.pending_start
                    after = pending_after_proposal(before, start)
                    session.recorder.record(
                        "deterministic",
                        "pending_after_proposal",
                        {"pending_start": before, "proposed_start": start},
                        {"pending_start": after}
                    )
                    session.pending_start = after
                    result = (
                        f"proposal_pending:{start}; "
                        "tell the patient the exact slot and ask for confirmation"
                    )
            elif tool_call.function.name == "confirm_appointment":
                before = session.pending_start
                decision = pending_proposal_matches(
                    before, pending_at_turn_start
                )
                session.recorder.record(
                    "deterministic",
                    "pending_proposal_matches",
                    {
                        "pending_start": before,
                        "pending_at_turn_start": pending_at_turn_start
                    },
                    {"decision": decision}
                )

                if decision != "allow":
                    result = "refused: no earlier pending appointment to confirm"
                else:
                    start = pending_at_turn_start

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

                    is_in_future = not_in_past(start, session.now)
                    session.recorder.record(
                        "deterministic",
                        "not_in_past",
                        {"start": start, "now": session.now},
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
                    else:
                        result = "refused: requested slot is in past"

                after = pending_after_resolution(before, pending_at_turn_start)
                session.recorder.record(
                    "deterministic",
                    "pending_after_resolution",
                    {
                        "pending_start": before,
                        "pending_at_turn_start": pending_at_turn_start
                    },
                    {"pending_start": after}
                )
                session.pending_start = after
            elif tool_call.function.name == "decline_proposal":
                before = session.pending_start
                decision = pending_proposal_matches(
                    before, pending_at_turn_start
                )
                session.recorder.record(
                    "deterministic",
                    "pending_proposal_matches",
                    {
                        "pending_start": before,
                        "pending_at_turn_start": pending_at_turn_start
                    },
                    {"decision": decision}
                )

                after = pending_after_resolution(before, pending_at_turn_start)
                session.recorder.record(
                    "deterministic",
                    "pending_after_resolution",
                    {
                        "pending_start": before,
                        "pending_at_turn_start": pending_at_turn_start
                    },
                    {"pending_start": after}
                )
                session.pending_start = after

                if decision == "allow":
                    result = "declined: current appointment proposal was declined"
                else:
                    result = "there was no earlier pending proposal to decline."

            else:
                result = f"refused: unsupported tool {tool_call.function.name}"

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
