"""
The agent: a model proposes a booking, the guards decide, the effect acts,
and every step is recorded. A reply with no tool call, and a tool call whose
arguments are not valid JSON, each end the run with the trace saved.

Run from the repo root with the .env exported:
    set -a; source .env; set +a
    python -m clinic.agent
"""

import json
import os

from openai import OpenAI

from clinic.guards import slot_is_free, within_opening_hours, not_in_past
from clinic.trace import Recorder
from clinic.world import BOOKED, CLINIC_NAME, SLOT_MINUTES, OPEN_TIME, CLOSE_TIME

model_name = os.environ.get("MODEL_NAME")
model_api_key = os.environ.get("MODEL_API_KEY")
model_base_url = os.environ.get("MODEL_BASE_URL")

NOW = "2026-10-01T09:12"
RUN_ID = "conv-0004"
TRACE_PATH = f"traces/{RUN_ID}.json"

rec = Recorder(RUN_ID)
client = OpenAI(
    base_url=model_base_url,
    api_key=model_api_key
)

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
        "content": "Book me Monday 12 Oct at 10:00"
    }
]

tools = [{
    "type": "function",
    "function": {
        "name": "book_appointment",
        "description": "use this tool when patient wants to book an appointment",
        "parameters": {
            "type": "object",
            "properties": {
                "start": {
                    "type": "string",
                    "description": "start of the slot in the format is 2026-10-13T15:00"
                }
            },
            "required": ["start"]
        }
    }
}]

# 1. The patient speaks.
rec.record("nondeterministic", "user_message", {}, {"text": messages[1]["content"]})

# 2. The model proposes: a plain reply, or a tool call.
first = client.chat.completions.create(
    model=model_name,
    messages=messages,
    tools=tools
)
message = first.choices[0].message

# No tool call is a normal outcome: the model answered in text. Record the
# reply and stop.
if message.tool_calls is None:
    rec.record("nondeterministic", "agent_reply", {}, {"text": message.content})
    rec.save(TRACE_PATH)
    print(message.content)
    raise SystemExit

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

# Arguments that are not valid JSON are a broken output, not a normal one.
# Record why the run stops, save the trace, and stop.
try:
    start = json.loads(tool_call.function.arguments)["start"]
except json.JSONDecodeError:
    rec.record(
        "deterministic",
        "json",
        {"arguments": tool_call.function.arguments},
        {"decision": "json.load error"}
    )
    rec.save(TRACE_PATH)
    print("json.load error")
    raise SystemExit

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
    rec.record("nondeterministic", "book_appointment", {"start": start}, {"booked": True})
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

second = client.chat.completions.create(
    model=model_name,
    messages=messages,
    tools=tools
)
reply = second.choices[0].message.content
rec.record("nondeterministic", "agent_reply", {}, {"text": reply})

rec.save(TRACE_PATH)
print(reply)
