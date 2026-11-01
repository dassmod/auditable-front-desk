"""Run the in-progress browser voice prototype with Pipecat.

The prototype opens a SmallWebRTC audio transport, detects speech turns with
Silero VAD, and creates a clinic API session for each connected client. Speech
recognition, clinic-message forwarding, and spoken replies are not wired yet.
"""

import httpx
from dotenv import load_dotenv
from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.audio.vad_processor import VADProcessor
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.workers.runner import WorkerRunner


load_dotenv()


transport_params = {
    "webrtc": lambda: TransportParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
    )
}


async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    """Run the audio pipeline and create a clinic API session on connection."""
    pipeline = Pipeline(
        [
            transport.input(),
            VADProcessor(vad_analyzer=SileroVADAnalyzer()),
            transport.output(),
        ]
    )

    worker = PipelineWorker(pipeline, params=PipelineParams())
    runner = WorkerRunner(handle_sigint=runner_args.handle_sigint)
    await runner.add_workers(worker)

    api_client = httpx.AsyncClient(base_url="http://127.0.0.1:8000")
    clinic_session_id: str | None = None

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        """Create the clinic-side session for this browser conversation."""
        nonlocal clinic_session_id

        response = await api_client.post("/sessions")
        response.raise_for_status()
        clinic_session_id = response.json()["session_id"]
        logger.info("Clinic session created: {}", clinic_session_id)

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        """Stop the pipeline after the browser client disconnects."""
        logger.info("Browser voice client disconnected")
        await runner.cancel()

    try:
        await runner.run()
    finally:
        await api_client.aclose()


async def bot(runner_args: RunnerArguments):
    """Pipecat runner entry point for one browser voice conversation."""
    transport = await create_transport(runner_args, transport_params)
    await run_bot(transport, runner_args)


if __name__ == "__main__":
    from pipecat.runner.run import main

    main()
