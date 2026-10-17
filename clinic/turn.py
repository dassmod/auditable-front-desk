"""One patient turn on a Session."""

import os

model_name = os.environ.get("MODEL_NAME")

def run_turn(session, text):
    """Record the patient's message in the trace and in the message list.

    The model call, the guards and the reply are not here yet.
    """
    session.recorder.record(
        "nondeterministic", "user_message", {}, {"text": text}
    )
    session.messages.append({"role": "user", "content": text})

    response = session.client.chat.completions.create(
        model=model_name,
        messages=session.messages
    )

    message = response.choices[0].message
    session.recorder.record("nondeterministic", "agent_reply", {}, {"text": message.content})
    session.messages.append({
        "role": "assistant",
        "content": message.content
    })

    return message.content