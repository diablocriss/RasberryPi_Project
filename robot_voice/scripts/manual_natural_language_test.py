from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.optimized_pipeline import OptimizedRobotPipeline


NATURAL_LANGUAGE_COMMANDS = [
    "go ahead",
    "please drive straight for a moment",
    "move forwards please",
    "go back",
    "reverse",
    "turn left",
    "spin left",
    "turn right",
    "spin right",
    "faster",
    "speed up",
    "slow down",
    "slower",
    "halt",
    "freeze",
    "stop",
    "tien len",
    "di thang",
    "lui lai",
    "xoay trai",
    "xoay phai",
    "dung lai",
]


def run_cases(pipeline: OptimizedRobotPipeline, cases: list[str], verbose: bool) -> None:
    for index, text in enumerate(cases, start=1):
        started = time.perf_counter()
        result = pipeline.process(text, verbose=verbose)
        elapsed_ms = (time.perf_counter() - started) * 1000
        print(f"\n[{index:02d}] {text}")
        print(json.dumps(result, indent=2))
        print(f"elapsed_ms={elapsed_ms:.2f}")


def interactive_loop(pipeline: OptimizedRobotPipeline, verbose: bool) -> None:
    print("\nManual mode. Type a natural-language command, or 'quit' to exit.")
    while True:
        text = input("> ").strip()
        if text.lower() in {"q", "quit", "exit"}:
            break
        if not text:
            continue
        started = time.perf_counter()
        result = pipeline.process(text, verbose=verbose)
        elapsed_ms = (time.perf_counter() - started) * 1000
        print(json.dumps(result, indent=2))
        print(f"elapsed_ms={elapsed_ms:.2f}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Manual natural-language test for optimized robot commands.")
    parser.add_argument("--interactive", "-i", action="store_true", help="Type custom commands manually.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show timing and progress output.")
    args = parser.parse_args()

    pipeline = OptimizedRobotPipeline()
    run_cases(pipeline, NATURAL_LANGUAGE_COMMANDS, verbose=args.verbose)
    if args.interactive:
        interactive_loop(pipeline, verbose=args.verbose)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
