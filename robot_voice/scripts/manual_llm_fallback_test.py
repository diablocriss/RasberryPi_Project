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

from core.optimized_pipeline import OptimizedRobotPipeline, normalize_text


UNCOMMON_COMMANDS = [
    "advance a short distance",
    "roll ahead briefly",
    "retreat a little",
    "back away from the obstacle",
    "pivot toward the left side",
    "face the right wall",
    "increase your pace",
    "reduce your pace",
    "stay exactly where you are",
    "cancel movement immediately",
]


def is_rule_hit(pipeline: OptimizedRobotPipeline, text: str) -> bool:
    return pipeline.rule_matcher.match(normalize_text(text)) is not None


def main() -> int:
    parser = argparse.ArgumentParser(description="Manual LLM fallback timing test.")
    parser.add_argument("--model", help="Path to a llama.cpp GGUF model.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show per-stage timing.")
    parser.add_argument("commands", nargs="*", help="Optional custom uncommon commands.")
    args = parser.parse_args()

    pipeline = OptimizedRobotPipeline(model_path=args.model)
    commands = args.commands or UNCOMMON_COMMANDS

    model_available = pipeline.load()
    print(f"model_path={pipeline.model_path}")
    print(f"llm_loaded={model_available}")
    if not model_available:
        print("LLM is not available; unmatched commands will use validation fallback.")

    for index, text in enumerate(commands, start=1):
        rule_hit = is_rule_hit(pipeline, text)
        started = time.perf_counter()
        result = pipeline.process(text, verbose=args.verbose)
        elapsed = time.perf_counter() - started

        print(f"\n[{index:02d}] {text}")
        print(f"rule_hit_before_llm={rule_hit}")
        print(json.dumps(result, indent=2))
        print(f"elapsed_seconds={elapsed:.3f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
