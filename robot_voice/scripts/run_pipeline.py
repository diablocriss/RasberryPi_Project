import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> int:
    return subprocess.call(command, cwd=ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run robot voice pipeline modes")
    parser.add_argument("mode", choices=["check", "text", "usb", "live"], nargs="?", default="check")
    args = parser.parse_args()
    return run(["bash", "scripts/pi_process.sh", args.mode])


if __name__ == "__main__":
    sys.exit(main())
