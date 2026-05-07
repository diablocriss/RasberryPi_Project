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

LLM_BENCHMARK_CASES = [
    ("edge forward a touch", "MOVE", "FORWARD"),
    ("ease backward for a moment", "MOVE", "BACKWARD"),
    ("angle yourself slightly to the left", "TURN", "LEFT"),
    ("orient toward the right side", "TURN", "RIGHT"),
    ("bring everything to a standstill", "STOP", None),
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


async def run_llm_benchmark(cases: list[tuple[str, str, str | None]]) -> int:
    processor = OllamaCommandProcessor()
    passed = 0
    total_rule = 0.0
    total_cache = 0.0
    total_ollama = 0.0
    total_end_to_end = 0.0
    source_counts: dict[str, int] = {}

    try:
        for text, expected_cmd, expected_dir in cases:
            started = time.perf_counter()
            command = await processor.process_async(text, use_llm=True)
            elapsed = time.perf_counter() - started
            metrics = processor.metrics()
            source = str(metrics["source"])
            source_counts[source] = source_counts.get(source, 0) + 1
            total_rule += float(metrics["rule_match_s"])
            total_cache += float(metrics["cache_lookup_s"])
            total_ollama += float(metrics["ollama_latency_s"])
            total_end_to_end += float(metrics["total_s"])

            ok = command["cmd"] == expected_cmd and (expected_dir is None or command.get("dir") == expected_dir)
            passed += int(ok)

            print(f"\n{text}")
            print(json.dumps(command, indent=2))
            print(json.dumps(metrics, indent=2))
            print(f"elapsed_s={elapsed:.3f} ok={ok}")

        count = len(cases) or 1
        avg_rule = total_rule / count
        avg_cache = total_cache / count
        avg_ollama = total_ollama / count
        avg_total = total_end_to_end / count

        dominant_stage = "ollama"
        dominant_value = avg_ollama
        if avg_rule > dominant_value:
            dominant_stage = "rule_match"
            dominant_value = avg_rule
        if avg_cache > dominant_value:
            dominant_stage = "cache_lookup"
            dominant_value = avg_cache
        if (avg_total - avg_rule - avg_cache - avg_ollama) > dominant_value:
            dominant_stage = "other"

        print("\nbenchmark_summary")
        print(json.dumps({
            "cases": count,
            "passed": passed,
            "source_counts": source_counts,
            "avg_rule_match_s": round(avg_rule, 6),
            "avg_cache_lookup_s": round(avg_cache, 6),
            "avg_ollama_latency_s": round(avg_ollama, 6),
            "avg_total_s": round(avg_total, 6),
            "dominant_stage": dominant_stage,
        }, indent=2))
    finally:
        await processor.close()
    return passed


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Ollama robot command pipeline.")
    parser.add_argument("--live", action="store_true", help="Include Ollama API fallback cases.")
    parser.add_argument("--llm-benchmark", action="store_true", help="Run unmatched natural-language cases and report stage timing.")
    args = parser.parse_args()

    if args.llm_benchmark:
        passed = asyncio.run(run_llm_benchmark(LLM_BENCHMARK_CASES))
        print(f"\npassed={passed}/{len(LLM_BENCHMARK_CASES)}")
        return 0 if passed == len(LLM_BENCHMARK_CASES) else 1

    cases = TEST_CASES + (LLM_CASES if args.live else [])
    passed = asyncio.run(run_live_cases(cases))
    print(f"\npassed={passed}/{len(cases)}")
    return 0 if passed >= 10 and passed == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
