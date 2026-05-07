#!/usr/bin/env python3
"""Standalone test for the edge-TTS engine used by the MoonShine pipeline.

Usage:
    python3 scripts/test_tts.py
    python3 scripts/test_tts.py "Hello, I am your robot"
    python3 scripts/test_tts.py --volume 3.0 "Louder test"
    python3 scripts/test_tts.py --volume 1.0 "Original loudness"

The --volume flag overrides configs/moonshine_config.yaml for this run only,
so you can A/B test gain without redeploying.
"""
import argparse
import logging
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tts.tts_engine import TTSEngine  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("text", nargs="*",
                        help="Text to speak (default: a built-in sentence)")
    parser.add_argument("--volume", type=float, default=None,
                        help="Override tts.volume (e.g. 1.5, 2.0, 3.0)")
    parser.add_argument("--config", type=Path,
                        default=ROOT / "configs" / "moonshine_config.yaml")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                        datefmt="%H:%M:%S")

    with open(args.config) as f:
        config = yaml.safe_load(f)

    if args.volume is not None:
        config.setdefault("tts", {})["volume"] = args.volume

    text = " ".join(args.text) or (
        "Hello, I am your robot assistant. Awaiting your command."
    )
    print(f"voice = {config['tts'].get('voice')}")
    print(f"rate  = {config['tts'].get('rate')}")
    print(f"volume= {config['tts'].get('volume')}")
    print(f"device= {config['audio'].get('device')}")
    print(f"text  = {text!r}")

    TTSEngine(config).say(text)


if __name__ == "__main__":
    main()
