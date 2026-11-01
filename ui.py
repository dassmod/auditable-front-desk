"""Gradio chat and replay-verification page for the clinic API.

`api.py` mounts `demo` at `/ui`, so both are served by one Uvicorn process.
For standalone development, run `python ui.py` while the API is on port 8000;
Gradio then serves this page on port 7860.
"""

import gradio as gr
import httpx

API = "http://127.0.0.1:8000"


def respond(message, history, session_id):
    """Send one patient message to the API and return its reply and session ID.

    The API session stores the conversation history; Gradio's `history`
    argument is accepted by the callback but is not the source of truth.
    """
    if session_id is None:
        session_id = httpx.post(f"{API}/sessions").json()["session_id"]
    response = httpx.post(
        f"{API}/sessions/{session_id}/messages",
        json={"text": message},
        timeout=60,
    )
    reply = response.json()["reply"]
    return reply, session_id


def verify(session_id):
    """Ask the API to replay the session trace and return its verdicts."""
    if session_id is None:
        return {"error": "Send a message first."}
    response = httpx.post(
        f"{API}/sessions/{session_id}/verify",
        timeout=60,
    )
    return response.json()


with gr.Blocks() as demo:
    sid = gr.State(None)
    gr.ChatInterface(
        fn=respond,
        additional_inputs=[sid],
        additional_outputs=[sid],
    )
    verify_button = gr.Button("Verify")
    verdicts = gr.JSON(label="Replay verdicts")

    verify_button.click(
        fn=verify,
        inputs=[sid],
        outputs=[verdicts],
    )

if __name__ == "__main__":
    demo.launch()
