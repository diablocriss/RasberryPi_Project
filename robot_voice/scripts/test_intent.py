"""Standalone smoke test for the trained FastText hotel-reception intent classifier.

Run from anywhere:
    python scripts/test_intent.py
    python scripts/test_intent.py "where is the gym"   # ad-hoc single utterance

Loads the model from src/intent/hotel_reception_intent.bin and prints predicted
intent + confidence + top-3 alternatives for a curated sample of utterances
(including off-topic ones to confirm the 'unknown' fallback).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from intent.classifier import IntentClassifier  # noqa: E402

GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
DIM = "\033[2m"
RESET = "\033[0m"

# Curated test set: clean cases + ASR-style typos + clearly off-topic samples.
SMOKE_SAMPLES: list[tuple[str, str]] = [
    # (utterance, expected_intent)
    ("hello there", "greeting"),
    ("good morning robot", "greeting"),
    ("bye bye see you tomorrow", "goodbye"),
    ("ok bye", "goodbye"),
    ("i would like to check in please", "check_in"),
    ("i have a reservation under smith", "check_in"),
    ("checkin", "check_in"),                       # typo
    ("can i check out", "check_out"),
    ("settle my bill please", "check_out"),
    ("how much per night for a deluxe room", "room_inquiry"),
    ("any rooms free tonight", "room_inquiry"),
    ("where is the gym", "facilities"),
    ("what time does breakfast start", "facilities"),
    ("whats the wifi password", "wifi"),
    ("wifi passwrd", "wifi"),                      # typo
    ("how do i get to my room", "directions"),
    ("which way to the elevator", "directions"),
    ("the air conditioning isnt working", "complaint"),
    ("can i speak to the manager", "complaint"),
    ("can you book me a taxi", "concierge"),
    ("recommend a good restaurant nearby", "concierge"),
    ("yes please", "confirm_yes"),
    ("yeah sure", "confirm_yes"),
    ("no thanks", "confirm_no"),
    ("nope", "confirm_no"),
    ("my name is john", "identity"),
    ("room two oh four", "identity"),
    ("thank you so much", "thanks"),
    ("thanks a lot", "thanks"),
    # Off-topic / nonsense -> should hit unknown via threshold or learned label
    ("whats the weather like outside", "unknown"),
    ("tell me a joke", "unknown"),
    ("asdf qwerty zzz", "unknown"),
    ("", "unknown"),                              # empty input
]


def _row(utt: str, result: dict, expected: str) -> str:
    intent = result["intent"]
    conf = result["confidence"]
    ok = intent == expected
    mark = f"{GREEN}OK{RESET}" if ok else f"{RED}MISS{RESET}"
    color = GREEN if ok else RED
    top3 = sorted(result["all_scores"].items(), key=lambda x: -x[1])[:3]
    top3_str = ", ".join(f"{lab}={p:.2f}" for lab, p in top3)
    return (
        f"  [{mark}] {color}{intent:14s}{RESET} {conf:.2f}  "
        f"expected={expected:14s} | {DIM}{utt!r:50s}{RESET}\n"
        f"        {DIM}top3: {top3_str}{RESET}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("text", nargs="?", help="single utterance to classify")
    parser.add_argument("--threshold", type=float, default=0.5,
                        help="confidence threshold below which prediction is 'unknown'")
    parser.add_argument("--model", default=None,
                        help="path to .bin (defaults to src/intent/hotel_reception_intent.bin)")
    args = parser.parse_args()

    print(f"{CYAN}== Intent classifier smoke test =={RESET}")
    clf = IntentClassifier(model_path=args.model, confidence_threshold=args.threshold)
    print(f"{DIM}model: {clf.model_path}{RESET}")
    print(f"{DIM}labels ({len(clf.labels)}): {', '.join(clf.labels)}{RESET}")
    print(f"{DIM}threshold: {clf.confidence_threshold}{RESET}\n")

    if args.text is not None:
        result = clf.predict(args.text)
        top3 = sorted(result["all_scores"].items(), key=lambda x: -x[1])[:3]
        print(f"input : {args.text!r}")
        print(f"intent: {GREEN}{result['intent']}{RESET}  (conf {result['confidence']:.2f})")
        print(f"top3  : {', '.join(f'{lab}={p:.2f}' for lab, p in top3)}")
        return 0

    correct = 0
    for utt, expected in SMOKE_SAMPLES:
        result = clf.predict(utt)
        print(_row(utt, result, expected))
        if result["intent"] == expected:
            correct += 1

    total = len(SMOKE_SAMPLES)
    pct = correct / total * 100
    color = GREEN if pct >= 90 else (YELLOW if pct >= 80 else RED)
    print(f"\n{color}Smoke-test accuracy: {correct}/{total} = {pct:.1f}%{RESET}")
    return 0 if pct >= 80 else 1


if __name__ == "__main__":
    raise SystemExit(main())
