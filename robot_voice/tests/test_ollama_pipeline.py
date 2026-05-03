from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.ollama_pipeline import OllamaCommandProcessor


TEST_CASES = [
    ("go ahead", "MOVE", "FORWARD"),
    ("drive straight", "MOVE", "FORWARD"),
    ("go back", "MOVE", "BACKWARD"),
    ("reverse", "MOVE", "BACKWARD"),
    ("spin left", "TURN", "LEFT"),
    ("go right", "TURN", "RIGHT"),
    ("halt", "STOP", None),
    ("freeze", "STOP", None),
    ("stop", "STOP", None),
    ("faster", "MOVE", "FORWARD"),
    ("slow down", "MOVE", "FORWARD"),
]

LLM_CASES = [
    ("advance a short distance", "MOVE", "FORWARD"),
    ("retreat a little", "MOVE", "BACKWARD"),
    ("pivot toward the left side", "TURN", "LEFT"),
]


def assert_command(command: dict, expected_cmd: str, expected_dir: str | None) -> None:
    assert command["cmd"] == expected_cmd
    if expected_dir is not None:
        assert command["dir"] == expected_dir


def test_fast_path_rules():
    processor = OllamaCommandProcessor()
    for text, expected_cmd, expected_dir in TEST_CASES:
        command = processor.process(text, use_llm=False)
        assert_command(command, expected_cmd, expected_dir)
        assert processor.metrics()["source"] == "rule"
        if text in {"faster", "slow down"}:
            assert command["time_ms"] == 300


async def run_live_cases(cases: list[tuple[str, str, str | None]]) -> int:
    processor = OllamaCommandProcessor()
    passed = 0
    try:
        for text, expected_cmd, expected_dir in cases:
            started = time.perf_counter()
            command = await processor.process_async(text, use_llm=True)
            elapsed = time.perf_counter() - started
            metrics = processor.metrics()
            ok = command["cmd"] == expected_cmd and (expected_dir is None or command.get("dir") == expected_dir)
            passed += int(ok)
            print(f"\n{text}")
            print(json.dumps(command, indent=2))
            print(json.dumps(metrics, indent=2))
            print(f"elapsed_s={elapsed:.3f} ok={ok}")
    finally:
        await processor.close()
    return passed


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Ollama robot command pipeline.")
    parser.add_argument("--live", action="store_true", help="Include Ollama API fallback cases.")
    args = parser.parse_args()

    cases = TEST_CASES + (LLM_CASES if args.live else [])
    passed = asyncio.run(run_live_cases(cases))
    print(f"\npassed={passed}/{len(cases)}")
    return 0 if passed >= 10 and passed == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
