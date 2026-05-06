#!/usr/bin/env python3
"""Measure RMS and peak level of a recorded WAV file.

Usage:
    python3 scripts/test_mic_rms.py
    python3 scripts/test_mic_rms.py --file /tmp/my_recording.wav
"""
import argparse
import math
import struct
import wave


def measure(path: str) -> None:
    with wave.open(path) as f:
        n = f.getnframes()
        frames = f.readframes(n)
        ch = f.getnchannels()
        rate = f.getframerate()
        width = f.getsampwidth()

    fmt = "<" + ("h" if width == 2 else "b") * (len(frames) // width)
    samples = struct.unpack(fmt, frames)
    max_val = 32768 if width == 2 else 128

    rms = math.sqrt(sum(s * s for s in samples) / len(samples))
    peak = max(abs(s) for s in samples)
    rms_db = 20 * math.log10(rms / max_val) if rms > 0 else -999
    peak_db = 20 * math.log10(peak / max_val) if peak > 0 else -999

    print(f"File     : {path}")
    print(f"Rate     : {rate} Hz  |  Channels: {ch}  |  Bit depth: {width * 8}-bit")
    print(f"Samples  : {len(samples)}")
    print(f"RMS      : {rms:.1f}  ({rms_db:.1f} dBFS)")
    print(f"Peak     : {peak}  ({peak_db:.1f} dBFS)")

    if rms < 50:
        print("WARNING  : Very low signal — check mic wiring or gain")
    elif rms_db > -6:
        print("WARNING  : Signal close to clipping")
    else:
        print("Level    : OK")


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure mic RMS level")
    parser.add_argument("--file", default="/tmp/test.wav", help="WAV file to analyse")
    args = parser.parse_args()
    measure(args.file)


if __name__ == "__main__":
    main()
