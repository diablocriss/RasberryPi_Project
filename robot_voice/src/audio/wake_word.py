import logging
import subprocess
import threading

import numpy as np

logger = logging.getLogger(__name__)

_BYTES_PER_S32 = 4


class _AudioStream:
    """Persistent arecord subprocess — open once, read forever."""

    def __init__(self, cfg: dict) -> None:
        audio = cfg.get("audio", {})
        self._device   = audio.get("device", "plughw:2,0")
        self._hw_rate  = audio.get("hw_rate", 48000)
        self._hw_ch    = audio.get("hw_channels", 2)
        self._target_rate = audio.get("target_rate", 16000)
        self._ratio    = self._hw_rate // self._target_rate
        chunk_ms       = audio.get("chunk_ms", 80)
        self._chunk_target = int(self._target_rate * chunk_ms / 1000)
        self._chunk_bytes  = self._chunk_target * self._ratio * self._hw_ch * _BYTES_PER_S32
        self._proc: subprocess.Popen | None = None

    def open(self) -> None:
        import time
        # Kill any stale arecord from a previous run
        subprocess.run(["pkill", "-f", f"arecord.*{self._device}"],
                       stderr=subprocess.DEVNULL)
        # Retry a few times: a previous arecord can still be releasing the
        # I2S device when we try to reopen, surfacing as "Device or
        # resource busy" for ~1 second after the parent process exits.
        last_err = ""
        for attempt in range(5):
            # stderr → PIPE + draining thread: undrained PIPE fills the
            # kernel buffer (~64 KB) and kills arecord, but DEVNULL hides
            # startup errors. The thread keeps the buffer empty and stashes
            # the last ~4 KB so we can surface any failure message.
            self._proc = subprocess.Popen(
                ["arecord", "-D", self._device, "-f", "S32_LE",
                 "-r", str(self._hw_rate), "-c", str(self._hw_ch), "-q"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            self._stderr_tail = bytearray()
            threading.Thread(
                target=self._drain_stderr, daemon=True
            ).start()
            time.sleep(0.3)
            if self._proc.poll() is None:
                logger.info("Audio stream opened (%s)", self._device)
                return
            last_err = bytes(self._stderr_tail).decode(errors="ignore").strip()
            logger.warning("arecord open attempt %d failed: %s",
                           attempt + 1, last_err or "(no stderr)")
            time.sleep(0.4)
        raise RuntimeError(
            f"arecord failed to start after retries: {last_err or '(no stderr)'}"
        )

    def _drain_stderr(self) -> None:
        """Continuously read arecord's stderr so its kernel pipe buffer
        never fills, while keeping the last few KB for diagnostics."""
        try:
            while True:
                data = self._proc.stderr.read(4096)
                if not data:
                    return
                self._stderr_tail += data
                if len(self._stderr_tail) > 4096:
                    del self._stderr_tail[: len(self._stderr_tail) - 4096]
        except Exception:
            pass

    def close(self) -> None:
        if self._proc:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                # arecord can block on a blocking I2S read and ignore SIGTERM
                self._proc.kill()
                try:
                    self._proc.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    pass
            self._proc = None
            logger.info("Audio stream closed")

    def pause(self) -> None:
        """Terminate arecord so PipeWire/ALSA see the capture stream end
        and stop ducking playback. SIGSTOP is not enough — the file
        descriptor stays open and PipeWire keeps the stream registered."""
        self.close()

    def resume(self) -> None:
        """Reopen arecord after TTS playback finishes."""
        self.open()

    def read_chunk(self) -> np.ndarray | None:
        """Blocking read — returns int16 mono at target_rate, or None if stream died."""
        raw = self._proc.stdout.read(self._chunk_bytes)
        if not raw or len(raw) < self._chunk_bytes:
            return None
        samples = np.frombuffer(raw, dtype=np.int32).reshape(-1, self._hw_ch)
        return (samples[:, 0][:: self._ratio] >> 16).astype(np.int16)

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *_):
        self.close()


class AudioCapture:
    """VAD-based recorder: waits for voice then records until silence.

    Open once with start() / use as context manager — keeps one arecord
    process alive for the whole session.
    """

    def __init__(self, config: dict) -> None:
        self._stream = _AudioStream(config)
        vad = config.get("vad", {})
        target_rate   = config.get("audio", {}).get("target_rate", 16000)
        chunk_ms      = config.get("audio", {}).get("chunk_ms", 80)
        self._target_rate    = target_rate
        self._chunk_ms       = chunk_ms
        self._record_seconds = vad.get("record_seconds", 6)
        self._silence_timeout= vad.get("silence_timeout", 1.5)
        self._silence_rms    = vad.get("silence_rms_threshold", 300)
        self._activity_rms   = vad.get("activity_rms_threshold", 800)

    def start(self) -> None:
        self._stream.open()

    def stop(self) -> None:
        self._stream.close()

    def pause(self) -> None:
        self._stream.pause()

    def resume(self) -> None:
        self._stream.resume()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *_):
        self.stop()

    def record_utterance(self) -> np.ndarray:
        """Block until voice detected, record until silence.
        Returns float32 16 kHz mono."""
        max_rec_chunks = int(self._record_seconds * 1000 / self._chunk_ms)
        silence_limit  = int(self._silence_timeout * 1000 / self._chunk_ms)

        frames: list[np.ndarray] = []
        silent  = 0
        started = False

        while True:
            chunk = self._stream.read_chunk()
            if chunk is None:
                # arecord died — raise so the pipeline stops loudly instead
                # of tight-looping with empty audio.
                rc = (self._stream._proc.returncode
                      if self._stream._proc else None)
                raise RuntimeError(
                    f"audio stream ended unexpectedly (arecord exit={rc})"
                )

            rms = float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2)))

            if not started:
                if rms >= self._activity_rms:
                    logger.info("Voice detected (rms=%.0f)", rms)
                    started = True
                    frames.append(chunk)
            else:
                frames.append(chunk)
                if rms < self._silence_rms:
                    silent += 1
                    if silent >= silence_limit:
                        break
                else:
                    silent = 0
                if len(frames) >= max_rec_chunks:
                    break

        if not frames:
            return np.array([], dtype=np.float32)

        audio = np.concatenate(frames).astype(np.float32) / 32768.0
        logger.info("Recorded %.2fs", len(audio) / self._target_rate)
        return audio
