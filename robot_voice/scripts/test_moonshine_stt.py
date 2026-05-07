#!/usr/bin/env python3
"""Quick test: record 3 seconds from I2S mic and transcribe with MoonShine."""

import sys
import subprocess
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from stt.moonshine_stt import MoonShineSTT

DEVICE = "plughw:2,0"
HW_RATE = 48000
HW_CHANNELS = 2
TARGET_RATE = 16000
DURATION = 3

print(f"Recording {DURATION}s from {DEVICE}... (speak now)")

raw = subprocess.run(
    ["arecord", "-D", DEVICE, "-f", "S32_LE",
     "-r", str(HW_RATE), "-c", str(HW_CHANNELS),
     "-d", str(DURATION), "-q"],
    capture_output=True,
).stdout

frame_bytes = HW_CHANNELS * 4  # S32_LE = 4 bytes per sample
raw = raw[: len(raw) - len(raw) % frame_bytes]
samples = np.frombuffer(raw, dtype=np.int32).reshape(-1, HW_CHANNELS)[:, 0]
samples = samples[:: HW_RATE // TARGET_RATE].astype(np.float32) / 2147483648.0

print(f"Audio: {len(samples)/TARGET_RATE:.2f}s  peak={np.abs(samples).max():.4f}")

stt = MoonShineSTT({})
text = stt.transcribe(samples)
print(f"Transcription: {text!r}")
