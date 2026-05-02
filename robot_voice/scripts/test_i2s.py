import argparse
import subprocess
from pathlib import Path


def run(command: list[str]) -> int:
    print("$", " ".join(command))
    return subprocess.call(command)


def main() -> int:
    parser = argparse.ArgumentParser(description="Test I2S microphone and speaker")
    parser.add_argument("--mic-device", default="default")
    parser.add_argument("--speaker-device", default="default")
    parser.add_argument("--seconds", type=int, default=3)
    args = parser.parse_args()

    wav = Path("/tmp/robot_voice_i2s_test.wav")
    capture = run(["arecord", "-D", args.mic_device, "-f", "S16_LE", "-r", "16000", "-c", "1", "-d", str(args.seconds), str(wav)])
    if capture != 0:
        return capture
    return run(["aplay", "-D", args.speaker_device, str(wav)])


if __name__ == "__main__":
    raise SystemExit(main())
