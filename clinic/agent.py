import os
from openai import OpenAI
import json
from clinic.guards import slot_is_free, within_opening_hours, not_in_past
from clinic.world import BOOKED, CLINIC_NAME, SLOT_MINUTES, OPEN_TIME, CLOSE_TIME

model_name = os.environ.get("MODEL_NAME")
model_api_key = os.environ.get("MODEL_API_KEY")
model_base_url = os.environ.get("MODEL_BASE_URL")

NOW = "2026-10-01T09:12"

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
            "content": "Book me in for next Tuesday at 3pm"
        }
    ]
tools=[{
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

first = client.chat.completions.create(
    model=model_name,
    messages=messages,
    tools=tools
)

start = json.loads(first.choices[0].message.tool_calls[0].function.arguments)["start"]
print(start)
is_free = slot_is_free(start, BOOKED)
is_open = within_opening_hours(start)
is_in_future = not_in_past(start, NOW)

if is_free == "allow" and is_open == "allow" and is_in_future == "allow":
    BOOKED.append(start)
    result = "booked"
elif is_free != "allow":
    result = "refused: not free"
elif is_open != "allow":
    result = "refused: office is not open"
elif is_in_future != "allow":
    result = "refused: requested slot is in past"

messages.append(first.choices[0].message)
messages.append({
    "role": "tool", 
    "tool_call_id": first.choices[0].message.tool_calls[0].id,
    "content": result
})

second = client.chat.completions.create(
    model=model_name,
    messages=messages,
    tools=tools
)

print(second.choices[0].message.content)