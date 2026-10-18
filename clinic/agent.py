"""
The agent: a conversation between a patient and a model that ends in a
booking, with every step recorded.

The model has two tools. `find_free_slots` is a read: the harness runs it,
records it and hands the list back, and the model goes on with no patient
turn in between. `book_appointment` is a proposal: it goes through the three
guards, and only if all of them allow does the effect run. The model then
writes the reply and the conversation goes on, so one run can hold several
bookings. A reply with no tool call is a question for the patient: it is
recorded, the patient answers, and the model is called again.

Typing quit saves the trace and ends the run. So does a booking whose
arguments cannot be read (not valid JSON, not an object, or no `start`). The
trace is also saved after every booking round. A crash anywhere else loses
the run. The arguments of `find_free_slots` are not checked yet.

The calendar is `BOOKED` in clinic/world.py, shared by the whole process.

Run from the repo root with the .env exported:
    set -a; source .env; set +a
    python -m clinic.agent
Change RUN_ID before each run: the trace is written to traces/<RUN_ID>.json
and an existing file of that name is overwritten.

clinic/turn.py runs the same loop on a Session, with no keyboard. This file
still holds its own copies of the system prompt (`fresh_messages` in
clinic/session.py), the tool list (`TOOLS` in clinic/tools.py) and `NOW` (in
clinic/session.py).
"""

import json
import os

from openai import OpenAI

from clinic.guards import slot_is_free, within_opening_hours, not_in_past
from clinic.trace import Recorder
from clinic.parser import parse_arguments
from clinic.world import (
    BOOKED, CLINIC_NAME, SLOT_MINUTES, OPEN_TIME, CLOSE_TIME
)
from clinic.tools import find_free_slots

# The model is reached through an OpenAI-shaped API. Three environment values
# pick the provider, the key and the model.
model_name = os.environ.get("MODEL_NAME")
model_api_key = os.environ.get("MODEL_API_KEY")
model_base_url = os.environ.get("MODEL_BASE_URL")

# The clock is fixed. It is told to the model, passed to `not_in_past` and
# recorded in the trace as an input.
NOW = "2026-10-01T09:12"
# One trace file per run, named after the run. Change it before each run.
RUN_ID = "conv-0018"
TRACE_PATH = f"traces/{RUN_ID}.json"

rec = Recorder(RUN_ID)
client = OpenAI(
    base_url=model_base_url,
    api_key=model_api_key
)

# The conversation the model sees: the system prompt, then the patient's
# first message, read from the keyboard.
messages = [
    {
        "role": "system",
        "content": f"""You are the front desk assistant for {CLINIC_NAME}, a clinic that books appointments.
The clinic is open Monday to Friday, from {OPEN_TIME} to {CLOSE_TIME}. Each appointment lasts {SLOT_MINUTES} minutes.
Today's date and time is {NOW}. Work out words like "tomorrow" or "next Tuesday" from this date.
When the patient has given a specific day and time, call book_appointment with start in the format YYYY-MM-DDTHH:MM, for example 2026-10-13T15:00.
If the day or time is unclear, ask the patient before calling the tool.
The booking system decides whether a slot is allowed. Never tell the patient an appointment is booked until the tool result says booked, and if it refuses, tell them the reason you were given."""
    },
    {
        "role": "user",
        "content": input("> ")
    }
]

# The two tools the model may call. `find_free_slots` is a read. With
# `book_appointment` the model only proposes: the guards decide and the effect
# acts.
tools = [
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

# 1. The patient speaks. This records only the first message. Every later
# one is recorded where it is read.
rec.record(
    "nondeterministic",
    "user_message",
    {},
    {"text": messages[1]["content"]}
)

# One pass of this loop is one booking proposal: ask, guard, act, reply, then
# read the patient's next message.
while True:
    # 2. The model answers one of three ways. A booking proposal leaves this
    # loop. A read tool call is answered here and the model is called again.
    # A plain reply is a question back to the patient: record it, add it and
    # the patient's answer to `messages`, and call the model again. The list
    # must not end on an assistant turn.
    while True:
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            tools=tools
        )
        message = response.choices[0].message

        if (
            message.tool_calls is not None
            and message.tool_calls[0].function.name == "book_appointment"
        ):
            break
        elif message.tool_calls is not None:
            # A read tool. Record the proposal, run the function, record its
            # answer and hand it back. The patient is not asked anything.
            tool_call = message.tool_calls[0]
            rec.record(
                "nondeterministic",
                "model_decision",
                {},
                {
                    "tool_name": tool_call.function.name,
                    "arguments": tool_call.function.arguments
                }
            )

            day = json.loads(tool_call.function.arguments)["day"]
            slots = find_free_slots(day, BOOKED)
            rec.record(
                "deterministic",
                "find_free_slots",
                {"day": day, "booked": BOOKED},
                {"slots": slots}
            )

            # The call goes into `messages` first, then its answer, joined to
            # the call by its id.
            messages.append(message)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(slots)
            })
            continue

        # A plain reply: a question for the patient.
        rec.record(
            "nondeterministic",
            "agent_reply",
            {},
            {"text": message.content}
        )
        print(message.content)
        messages.append(message)

        text = input("> ")
        if text == "quit":
            rec.save(TRACE_PATH)
            raise SystemExit

        rec.record("nondeterministic", "user_message", {}, {"text": text})
        messages.append({"role": "user", "content": text})

    tool_call = message.tool_calls[0]

    # Record the proposal as returned. `arguments` stays a JSON string.
    rec.record(
        "nondeterministic",
        "model_decision",
        {},
        {
            "tool_name": tool_call.function.name,
            "arguments": tool_call.function.arguments
        }
    )

    # Read the arguments with a pure function and record its status. Anything
    # but "ok" is a broken output: save the trace and stop.
    status = parse_arguments(tool_call.function.arguments)
    rec.record(
        "deterministic",
        "parse_arguments",
        {"arguments": tool_call.function.arguments},
        {"status": status}
    )

    if status != "ok":
        rec.save(TRACE_PATH)
        print(status)
        raise SystemExit

    start = json.loads(tool_call.function.arguments)["start"]

    # 3. The guards decide. Each is a pure function of its recorded inputs.
    is_free = slot_is_free(start, BOOKED)
    rec.record(
        "deterministic",
        "slot_is_free",
        {"start": start, "booked": BOOKED},
        {"decision": is_free}
    )

    is_open = within_opening_hours(start)
    rec.record(
        "deterministic",
        "within_opening_hours",
        {"start": start},
        {"decision": is_open}
    )

    is_in_future = not_in_past(start, NOW)
    rec.record(
        "deterministic",
        "not_in_past",
        {"start": start, "now": NOW},
        {"decision": is_in_future}
    )

    # 4. The effect acts, only when every guard allows.
    if is_free == "allow" and is_open == "allow" and is_in_future == "allow":
        BOOKED.append(start)
        rec.record(
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

    # 5. Send the result back and let the model write the reply.
    messages.append(message)
    messages.append({
        "role": "tool",
        "tool_call_id": tool_call.id,
        "content": result
    })

    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        tools=tools
    )
    reply = response.choices[0].message.content
    rec.record("nondeterministic", "agent_reply", {}, {"text": reply})

    # Save after every round, so a later crash keeps the bookings so far.
    rec.save(TRACE_PATH)
    print(reply)

    # 6. The patient answers. The model's reply goes into `messages` as an
    # assistant turn, so the next call sees what it said. Then read, check
    # for quit, record and append the patient's turn, as in stage 2.
    messages.append({"role": "assistant", "content": reply})

    text = input("> ")
    if text == "quit":
        rec.save(TRACE_PATH)
        raise SystemExit

    rec.record("nondeterministic", "user_message", {}, {"text": text})
    messages.append({"role": "user", "content": text})
