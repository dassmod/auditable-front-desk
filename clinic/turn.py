"""One patient turn on a Session."""


def run_turn(session, text):
    """Record the patient's message in the trace and in the message list.

    The model call, the guards and the reply are not here yet.
    """
    session.recorder.record(
        "nondeterministic", "user_message", {}, {"text": text}
    )
    session.messages.append({"role": "user", "content": text})
