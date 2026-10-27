import gradio as gr
import httpx

API = "http://127.0.0.1:8000"

def respond(message, history, session_id):
    if session_id is None:
        session_id = httpx.post(f"{API}/sessions").json()["session_id"]
    return session_id, session_id

with gr.Blocks() as demo:
    sid = gr.State(None)
    gr.ChatInterface(fn=respond, additional_inputs=[sid], additional_outputs=[sid])

if __name__ == "__main__":
    demo.launch()