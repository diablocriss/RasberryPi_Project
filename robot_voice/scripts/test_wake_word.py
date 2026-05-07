#!/usr/bin/env python3
"""Debug wake word detection: prints live scores while you speak."""

import sys
import subprocess
from pathlib import Path

import numpy as np
import openwakeword
from openwakeword.model import Model

HW_DEVICE   = "plughw:2,0"
HW_RATE     = 48000
HW_CHANNELS = 2
TARGET_RATE = 16000
RATIO       = HW_RATE // TARGET_RATE          # 3
CHUNK_MS    = 80
CHUNK_TARGET = int(TARGET_RATE * CHUNK_MS / 1000)   # 1280
CHUNK_HW     = CHUNK_TARGET * RATIO * HW_CHANNELS   # 7680 samples
CHUNK_BYTES  = CHUNK_HW * 4                          # S32_LE = 4 bytes

paths = [p for p in openwakeword.get_pretrained_model_paths() if "hey_jarvis" in p]
print(f"Loading model: {paths[0]}")
oww = Model(wakeword_model_paths=paths)

print(f"\nListening... say 'hey Jarvis' (Ctrl+C to stop)\n")

proc = subprocess.Popen(
    ["arecord", "-D", HW_DEVICE, "-f", "S32_LE",
     "-r", str(HW_RATE), "-c", str(HW_CHANNELS), "-q"],
    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
)

try:
    while True:
        raw = proc.stdout.read(CHUNK_BYTES)
        if not raw or len(raw) < CHUNK_BYTES:
            continue
        samples = np.frombuffer(raw, dtype=np.int32).reshape(-1, HW_CHANNELS)[:, 0]
        chunk   = (samples[::RATIO] >> 16).astype(np.int16)

        scores = oww.predict(chunk)
        # print any model that scores above 0.1 so we can see activity
        for name, score in scores.items():
            if score > 0.1:
                print(f"  {name}: {score:.3f}")
except KeyboardInterrupt:
    proc.terminate()
    print("Done.")
