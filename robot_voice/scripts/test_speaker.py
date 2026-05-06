#!/usr/bin/env python3
"""Speaker-only test for MAX98357 I2S amplifier.

Generates a sine-wave tone and plays it via aplay.
Run on the Pi:  python3 scripts/test_speaker.py
                python3 scripts/test_speaker.py --device hw:0,0 --freq 880
"""
import argparse
import math
import struct
import subprocess
import sys
import tempfile
import wave
from pathlib import Path


def generate_sine_wav(path: Path, freq: int, duration: float, rate: int, amplitude: float) -> None:
    num_samples = int(rate * duration)
    samples = [
        int(amplitude * 32767 * math.sin(2 * math.pi * freq * i / rate))
        for i in range(num_samples)
    ]
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)           # 16-bit
        wf.setframerate(rate)
        wf.writeframes(struct.pack(f"<{num_samples}h", *samples))


def main() -> int:
    parser = argparse.ArgumentParser(description="Test MAX98357 I2S speaker")
    parser.add_argument("--device", default="plughw:0,0",
                        help="ALSA playback device (default: plughw:0,0)")
    parser.add_argument("--freq", type=int, default=440,
                        help="Tone frequency in Hz (default: 440)")
    parser.add_argument("--duration", type=float, default=2.0,
                        help="Tone duration in seconds (default: 2.0)")
    parser.add_argument("--rate", type=int, default=44100,
                        help="Sample rate (default: 44100)")
    parser.add_argument("--volume", type=float, default=0.5,
                        help="Volume 0.0-1.0 (default: 0.5)")
    args = parser.parse_args()

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav_path = Path(f.name)

    try:
        print(f"[speaker-test] Generating {args.freq} Hz tone for {args.duration}s ...")
        generate_sine_wav(wav_path, args.freq, args.duration, args.rate, args.volume)

        cmd = ["aplay", "-D", args.device, str(wav_path)]
        print(f"[speaker-test] Running: {' '.join(cmd)}")
        result = subprocess.run(cmd)

        if result.returncode == 0:
            print("[speaker-test] OK — if you heard a tone, the speaker is working.")
        else:
            print("[speaker-test] aplay failed. Try a different --device value.", file=sys.stderr)
            print("[speaker-test] List available devices with:  aplay -l", file=sys.stderr)
        return result.returncode
    finally:
        wav_path.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
