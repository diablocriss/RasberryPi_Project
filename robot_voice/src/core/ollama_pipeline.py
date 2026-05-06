from __future__ import annotations

import asyncio
import ast
import json
import logging
import re
import time
import unicodedata
from collections import OrderedDict, deque
from dataclasses import dataclass
from typing import Any

try:
    import aiohttp
except ImportError:  # pragma: no cover - exercised on minimal installs
    aiohttp = None

Command = dict[str, Any]

LOGGER = logging.getLogger(__name__)


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, int(value)))


def normalize_text(text: str) -> str:
    text = text.strip().lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("đ", "d")
    text = re.sub(r"\b(please|now|robot|hey|ok|okay|nhe)\b", " ", text)
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


class LRUCache:
    def __init__(self, maxsize: int = 50) -> None:
        self.maxsize = maxsize
        self._data: OrderedDict[str, Command] = OrderedDict()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Command | None:
        if key not in self._data:
            self.misses += 1
            return None
        self.hits += 1
        self._data.move_to_end(key)
        return dict(self._data[key])

    def put(self, key: str, value: Command) -> None:
        self._data[key] = dict(value)
        self._data.move_to_end(key)
        if len(self._data) > self.maxsize:
            self._data.popitem(last=False)

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return 0.0 if total == 0 else self.hits / total


class SpeedContext:
    def __init__(self, default_speed: int = 150) -> None:
        self.current_speed = default_speed
        self.last_command: Command | None = None
        self.history: deque[Command] = deque(maxlen=5)

    def adjust_speed(self, delta: int) -> int:
        self.current_speed = _clamp(self.current_speed + delta, 0, 255)
        return self.current_speed

    def remember(self, command: Command) -> None:
        command = dict(command)
        if command.get("cmd") in {"MOVE", "TURN"} and "speed" in command:
            self.current_speed = _clamp(command["speed"], 0, 255)
        self.last_command = command
        self.history.append(command)


class RuleMatcher:
    def __init__(self, speed_context: SpeedContext) -> None:
        self.speed_context = speed_context
        self.exact_rules: dict[str, Command] = {
            "go ahead": {"cmd": "MOVE", "dir": "FORWARD", "speed": 150, "time_ms": 500},
            "drive straight": {"cmd": "MOVE", "dir": "FORWARD", "speed": 150, "time_ms": 500},
            "move forwards": {"cmd": "MOVE", "dir": "FORWARD", "speed": 150, "time_ms": 500},
            "move forward": {"cmd": "MOVE", "dir": "FORWARD", "speed": 150, "time_ms": 500},
            "go forward": {"cmd": "MOVE", "dir": "FORWARD", "speed": 150, "time_ms": 500},
            "forward": {"cmd": "MOVE", "dir": "FORWARD", "speed": 150, "time_ms": 500},
            "advance a short distance": {"cmd": "MOVE", "dir": "FORWARD", "speed": 150, "time_ms": 500},
            "roll ahead briefly": {"cmd": "MOVE", "dir": "FORWARD", "speed": 150, "time_ms": 500},
            "go back": {"cmd": "MOVE", "dir": "BACKWARD", "speed": 100, "time_ms": 500},
            "reverse": {"cmd": "MOVE", "dir": "BACKWARD", "speed": 100, "time_ms": 500},
            "go backward": {"cmd": "MOVE", "dir": "BACKWARD", "speed": 100, "time_ms": 500},
            "move backward": {"cmd": "MOVE", "dir": "BACKWARD", "speed": 100, "time_ms": 500},
            "backward": {"cmd": "MOVE", "dir": "BACKWARD", "speed": 100, "time_ms": 500},
            "retreat a little": {"cmd": "MOVE", "dir": "BACKWARD", "speed": 100, "time_ms": 500},
            "turn left": {"cmd": "TURN", "dir": "LEFT", "speed": 150, "time_ms": 500},
            "spin left": {"cmd": "TURN", "dir": "LEFT", "speed": 150, "time_ms": 500},
            "go left": {"cmd": "TURN", "dir": "LEFT", "speed": 150, "time_ms": 500},
            "turn right": {"cmd": "TURN", "dir": "RIGHT", "speed": 150, "time_ms": 500},
            "spin right": {"cmd": "TURN", "dir": "RIGHT", "speed": 150, "time_ms": 500},
            "go right": {"cmd": "TURN", "dir": "RIGHT", "speed": 150, "time_ms": 500},
            "halt": {"cmd": "STOP", "time_ms": 0},
            "freeze": {"cmd": "STOP", "time_ms": 0},
            "stop": {"cmd": "STOP", "time_ms": 0},
            "emergency stop": {"cmd": "STOP", "time_ms": 0},
            "tien len": {"cmd": "MOVE", "dir": "FORWARD", "speed": 150, "time_ms": 500},
            "di thang": {"cmd": "MOVE", "dir": "FORWARD", "speed": 150, "time_ms": 500},
            "lui lai": {"cmd": "MOVE", "dir": "BACKWARD", "speed": 100, "time_ms": 500},
            "xoay trai": {"cmd": "TURN", "dir": "LEFT", "speed": 150, "time_ms": 500},
            "xoay phai": {"cmd": "TURN", "dir": "RIGHT", "speed": 150, "time_ms": 500},
            "dung lai": {"cmd": "STOP", "time_ms": 0},
        }
        self.dynamic_exact = {
            "faster": 50,
            "speed up": 50,
            "increase your pace": 50,
            "nhanh hon": 50,
            "slow down": -30,
            "slower": -30,
            "reduce your pace": -30,
            "cham lai": -30,
        }
        self.regex_rules: list[tuple[re.Pattern[str], Command]] = [
            (re.compile(r"\b(go|move|drive|run|head|roll)\s+(ahead|forward|forwards|straight)\b|\badvance\b"),
             {"cmd": "MOVE", "dir": "FORWARD", "speed": 150, "time_ms": 500}),
            (re.compile(r"\b(go|move|drive)\s+(back|backward|backwards)\b|\breverse\b|\bretreat\b|\bback away\b"),
             {"cmd": "MOVE", "dir": "BACKWARD", "speed": 100, "time_ms": 500}),
            (re.compile(r"\b(turn|spin|rotate|pivot)\b.*\bleft\b"),
             {"cmd": "TURN", "dir": "LEFT", "speed": 150, "time_ms": 500}),
            (re.compile(r"\b(turn|spin|rotate|pivot|face)\b.*\bright\b"),
             {"cmd": "TURN", "dir": "RIGHT", "speed": 150, "time_ms": 500}),
            (re.compile(r"\b(stop|halt|freeze|pause|wait|hold|abort|stay|cancel)\b"),
             {"cmd": "STOP", "time_ms": 0}),
        ]
        self.dynamic_patterns: list[tuple[re.Pattern[str], int]] = [
            (re.compile(r"\b(faster|speed up|accelerate|quicker|increase.*pace|nhanh hon)\b"), 50),
            (re.compile(r"\b(slow down|slower|decelerate|reduce speed|reduce.*pace|cham lai)\b"), -30),
        ]

    def match(self, normalized_text: str) -> Command | None:
        if normalized_text in self.dynamic_exact:
            return self._speed_command(self.dynamic_exact[normalized_text])
        if normalized_text in self.exact_rules:
            return dict(self.exact_rules[normalized_text])
        for pattern, delta in self.dynamic_patterns:
            if pattern.search(normalized_text):
                return self._speed_command(delta)
        for pattern, command in self.regex_rules:
            if pattern.search(normalized_text):
                return dict(command)
        return None

    def _speed_command(self, delta: int) -> Command:
        return {
            "cmd": "MOVE",
            "dir": "FORWARD",
            "speed": self.speed_context.adjust_speed(delta),
            "time_ms": 300,
        }


@dataclass
class PipelineMetrics:
    rule_match_s: float = 0.0
    cache_lookup_s: float = 0.0
    ollama_latency_s: float = 0.0
    total_s: float = 0.0
    source: str = "fallback"
    cache_hit_rate: float = 0.0


class OllamaClient:
    def __init__(
        self,
        base_url: str,
        model_name: str,
        timeout_s: float = 8.0,
        max_retries: int = 2,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self._session: Any = None
        self._last_health_check = 0.0
        self._healthy = False

    async def _get_session(self) -> Any:
        if aiohttp is None:
            raise RuntimeError("aiohttp is not installed; run pip install aiohttp")
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout_s)
            connector = aiohttp.TCPConnector(limit=4, ttl_dns_cache=300)
            self._session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        return self._session

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()

    async def health_check(self, force: bool = False) -> bool:
        now = time.monotonic()
        if not force and now - self._last_health_check < 30:
            return self._healthy
        self._last_health_check = now
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/api/tags") as response:
                self._healthy = response.status == 200
        except Exception as exc:
            LOGGER.warning("Ollama health check failed: %s", exc)
            self._healthy = False
        return self._healthy

    async def query(self, prompt: str) -> str:
        if not await self.health_check():
            raise RuntimeError("Ollama server is not healthy")

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 64,
                "top_k": 40,
                "top_p": 0.9,
                "num_ctx": 512,
                "num_thread": 4,
                "num_batch": 32,
                "repeat_penalty": 1.05,
            },
        }

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                session = await self._get_session()
                async with session.post(f"{self.base_url}/api/generate", json=payload) as response:
                    response.raise_for_status()
                    result = await response.json()
                    return str(result.get("response", ""))
            except Exception as exc:
                last_error = exc
                self._healthy = False
                LOGGER.warning("Ollama generation failed on attempt %s: %s", attempt + 1, exc)
                await asyncio.sleep(0.2 * (attempt + 1))
                await self.health_check(force=True)
        raise RuntimeError(f"Ollama generation failed: {last_error}")


class OllamaCommandProcessor:
    def __init__(self, model_name: str = "robot-command", host: str = "localhost", port: int = 11434) -> None:
        self.model_name = model_name
        self.base_url = f"http://{host}:{port}"
        self.speed_context = SpeedContext()
        self.rules = RuleMatcher(self.speed_context)
        self.cache = LRUCache(50)
        self.client = OllamaClient(self.base_url, model_name)
        self._llm_lock = asyncio.Lock()
        self.last_metrics = PipelineMetrics()

    async def process_async(self, text: str, use_llm: bool = True) -> Command:
        started_total = time.perf_counter()
        normalized = normalize_text(text)
        metrics = PipelineMetrics()

        started = time.perf_counter()
        command = self.rules.match(normalized)
        metrics.rule_match_s = time.perf_counter() - started
        if command is not None:
            metrics.source = "rule"
            return self._finish(command, metrics, started_total)

        started = time.perf_counter()
        cached = self.cache.get(normalized)
        metrics.cache_lookup_s = time.perf_counter() - started
        if cached is not None:
            metrics.source = "cache"
            return self._finish(cached, metrics, started_total)

        if use_llm:
            try:
                prompt = self._build_prompt(text)
                started = time.perf_counter()
                async with self._llm_lock:
                    raw = await self.client.query(prompt)
                metrics.ollama_latency_s = time.perf_counter() - started
                command = self._parse_and_validate(raw, normalized)
                if command is not None:
                    self.cache.put(normalized, command)
                    metrics.source = "ollama"
                    return self._finish(command, metrics, started_total)
            except Exception as exc:
                LOGGER.error("Ollama unavailable; continuing in degraded rule-only mode: %s", exc)

        metrics.source = "fallback"
        return self._finish({"cmd": "STOP", "time_ms": 0}, metrics, started_total)

    def process(self, text: str, use_llm: bool = True) -> Command:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.process_async(text, use_llm=use_llm))
        raise RuntimeError("Use await process_async() when already inside an event loop")

    async def close(self) -> None:
        await self.client.close()

    def _build_prompt(self, text: str) -> str:
        recent = json.dumps(list(self.speed_context.history), separators=(",", ":"))
        return (
            "Parse this robot command into exactly one JSON object. "
            "Use keys cmd, dir, speed, time_ms. "
            f"Current speed is {self.speed_context.current_speed}. "
            f"Recent commands: {recent}. "
            f"User command: {text}"
        )

    def _parse_and_validate(self, raw: str, normalized_text: str) -> Command | None:
        command = self._parse_json(raw)
        if command is None:
            command = self._parse_text(raw)
        if command is None:
            return self.rules.match(normalized_text)
        return self._validate(command)

    def _parse_json(self, raw: str) -> Command | None:
        if not raw:
            return None
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start < 0 or end <= start:
            return None
        fragment = raw[start:end]
        try:
            parsed = json.loads(fragment)
        except json.JSONDecodeError:
            try:
                parsed = ast.literal_eval(fragment)
            except (SyntaxError, ValueError):
                return None
        return parsed if isinstance(parsed, dict) else None

    def _parse_text(self, raw: str) -> Command | None:
        text = normalize_text(raw)
        if "stop" in text:
            return {"cmd": "STOP", "time_ms": 0}
        if "back" in text or "reverse" in text:
            return {"cmd": "MOVE", "dir": "BACKWARD", "speed": 100, "time_ms": 500}
        if "left" in text:
            return {"cmd": "TURN", "dir": "LEFT", "speed": 150, "time_ms": 500}
        if "right" in text:
            return {"cmd": "TURN", "dir": "RIGHT", "speed": 150, "time_ms": 500}
        if "forward" in text or "ahead" in text or "move" in text:
            return {"cmd": "MOVE", "dir": "FORWARD", "speed": 150, "time_ms": 500}
        return None

    def _validate(self, command: Command) -> Command | None:
        cmd = str(command.get("cmd") or command.get("command") or "").upper()
        direction = str(command.get("dir") or command.get("direction") or "").upper()

        if cmd == "STOP":
            return {"cmd": "STOP", "time_ms": 0}
        if cmd == "MOVE":
            if direction not in {"FORWARD", "BACKWARD"}:
                return None
            speed = _clamp(command.get("speed", 150 if direction == "FORWARD" else 100), 1, 255)
            if direction == "BACKWARD" and speed == 0:
                speed = 100
            time_ms = _clamp(command.get("time_ms", 500), 100, 5000)
            return {"cmd": "MOVE", "dir": direction, "speed": speed, "time_ms": time_ms}
        if cmd == "TURN":
            if direction not in {"LEFT", "RIGHT"}:
                return None
            time_ms = _clamp(command.get("time_ms", 500), 100, 5000)
            return {"cmd": "TURN", "dir": direction, "speed": _clamp(command.get("speed", 150), 1, 255), "time_ms": time_ms}
        return None

    def _finish(self, command: Command, metrics: PipelineMetrics, total_start: float) -> Command:
        command = self._validate(command) or {"cmd": "STOP", "time_ms": 0}
        self.speed_context.remember(command)
        metrics.total_s = time.perf_counter() - total_start
        metrics.cache_hit_rate = self.cache.hit_rate
        self.last_metrics = metrics
        return command

    def metrics(self) -> dict[str, Any]:
        return {
            "rule_match_s": self.last_metrics.rule_match_s,
            "cache_lookup_s": self.last_metrics.cache_lookup_s,
            "ollama_latency_s": self.last_metrics.ollama_latency_s,
            "total_s": self.last_metrics.total_s,
            "source": self.last_metrics.source,
            "cache_hit_rate": self.last_metrics.cache_hit_rate,
            "current_speed": self.speed_context.current_speed,
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    processor = OllamaCommandProcessor()
    for phrase in ["go ahead", "reverse", "pivot toward the left side", "halt"]:
        result = processor.process(phrase)
        print(phrase, "=>", result, processor.metrics())
