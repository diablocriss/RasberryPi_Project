from __future__ import annotations

import asyncio
from typing import Any

try:
    from core.ollama_pipeline import (
        LRUCache,
        OllamaClient,
        OllamaCommandProcessor,
        RuleMatcher,
        SpeedContext,
        normalize_text,
    )
except ModuleNotFoundError:
    from src.core.ollama_pipeline import (
        LRUCache,
        OllamaClient,
        OllamaCommandProcessor,
        RuleMatcher,
        SpeedContext,
        normalize_text,
    )

Command = dict[str, Any]


class OptimizedRobotPipeline(OllamaCommandProcessor):
    """Backward-compatible name for the Ollama + Gemma3 command pipeline."""

    def __init__(
        self,
        model_path: str | None = None,
        progress_callback: Any | None = None,
        cache_size: int = 50,
        model_name: str = "robot-command",
        host: str = "localhost",
        port: int = 11434,
    ) -> None:
        super().__init__(model_name=model_name, host=host, port=port)
        self.cache = LRUCache(cache_size)
        self.progress_callback = progress_callback
        self.model_path = model_path

    def resolve(self, text: str, verbose: bool = False) -> tuple[Command | None, float]:
        command = self.process(text, use_llm=True)
        confidence = 0.0 if command["cmd"] == "STOP" and normalize_text(text) not in {"stop", "halt", "freeze"} else 1.0
        if verbose:
            print(command)
            print(self.metrics())
        return command, confidence

    def load(self) -> bool:
        try:
            return asyncio.run(self.client.health_check(force=True))
        except RuntimeError:
            return False

    def unload(self) -> None:
        try:
            asyncio.run(self.close())
        except RuntimeError:
            pass

    def cache_stats(self) -> dict[str, Any]:
        return {
            "cached_phrases": len(self.cache._data),
            "cache_hit_rate": self.cache.hit_rate,
            "current_speed": self.speed_context.current_speed,
            "history_size": len(self.speed_context.history),
        }
