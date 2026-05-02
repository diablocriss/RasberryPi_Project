import asyncio
import queue
import threading
from typing import Any

import numpy as np
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveOptions,
    LiveTranscriptionEvents,
)

_text_queue: queue.Queue[str] = queue.Queue()
_connection = None
_loop = None
_thread = None


def _start_deepgram(api_key: str, language: str = "en-US") -> None:
    global _connection, _loop, _thread

    def run() -> None:
        global _loop, _connection
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
        _loop.run_until_complete(_connect(api_key, language))

    _thread = threading.Thread(target=run, daemon=True)
    _thread.start()

    import time

    for _ in range(20):
        if _connection is not None:
            break
        time.sleep(0.2)


async def _connect(api_key: str, language: str) -> None:
    global _connection

    client = DeepgramClient(
        api_key,
        DeepgramClientOptions(options={"keepalive": "true"}),
    )

    _connection = client.listen.live.v("1")

    def on_open(self, open, **kwargs):
        print("[STT] WebSocket opened")

    def on_close(self, close, **kwargs):
        print("[STT] WebSocket closed")

    def on_transcript(self, result, **kwargs):
        try:
            transcript = result.channel.alternatives[0].transcript.strip()
            print(f"[STT] Transcript: '{transcript}'")
            if transcript:
                _text_queue.put(transcript)
        except Exception as exc:
            print(f"[STT] on_transcript error: {exc}")

    def on_error(self, error, **kwargs):
        print(f"[STT] Deepgram error: {error}")

    _connection.on(LiveTranscriptionEvents.Open, on_open)
    _connection.on(LiveTranscriptionEvents.Close, on_close)
    _connection.on(LiveTranscriptionEvents.Transcript, on_transcript)
    _connection.on(LiveTranscriptionEvents.Error, on_error)

    options = LiveOptions(
        language=language,
        model="nova-2",
        encoding="linear16",
        sample_rate=16000,
        channels=1,
        interim_results=False,
        punctuate=False,
    )

    _connection.start(options)
    print("[STT] Deepgram connection started")

    while True:
        await asyncio.sleep(1)


def stt_init(api_key: str, language: str = "en-US") -> None:
    if not api_key:
        raise RuntimeError("DEEPGRAM_API_KEY is not set")
    _start_deepgram(api_key, language)
    print("[STT] Deepgram WebSocket ready")


def stt_send(audio: Any) -> None:
    global _connection
    if _connection is None:
        print("[STT] WARNING: connection is not ready")
        return

    if isinstance(audio, np.ndarray):
        raw = audio.astype(np.int16).tobytes()
    else:
        raw = bytes(audio)

    _connection.send(raw)


def stt_get_text() -> str | None:
    try:
        return _text_queue.get_nowait()
    except queue.Empty:
        return None


def stt_process(audio: Any) -> str | None:
    stt_send(audio)
    return stt_get_text()
