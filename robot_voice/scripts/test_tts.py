#!/usr/bin/env python3
"""Test Piper TTS through MAX98357 speaker.

Usage:
    python3 scripts/test_tts.py
    python3 scripts/test_tts.py "Hello, I am your robot"
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tts.piper_tts import PiperTTS
from config.settings import Settings

text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Hello, I am your robot assistant. Awaiting your command."

print(f"Speaking: {text!r}")
PiperTTS(Settings()).say(text)
