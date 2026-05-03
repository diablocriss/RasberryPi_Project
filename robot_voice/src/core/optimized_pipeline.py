import json
import re
import time
import unicodedata
import ast
from collections import OrderedDict, deque
from inspect import signature
from pathlib import Path
from typing import Any, Callable

try:
    from config.settings import Settings
except ModuleNotFoundError:
    from src.config.settings import Settings

Command = dict[str, Any]
ProgressCallback = Callable[[str], None]


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def _copy_command(command: Command) -> Command:
    return dict(command)


def normalize_text(text: str) -> str:
    """Lowercase, strip Vietnamese diacritics, remove filler words, and collapse spaces."""
    text = text.strip().lower()
    normalized = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    text = text.replace("đ", "d")
    text = re.sub(r"\b(please|now|robot|can you|could you|hey|ok|okay|nhe)\b", " ", text)
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


class Timer:
    def __init__(self, verbose: bool = False, progress_callback: ProgressCallback | None = None) -> None:
        self.verbose = verbose
        self.progress_callback = progress_callback
        self._total_start = time.perf_counter()

    def progress(self, stage: int, total: int, message: str) -> None:
        line = f"[PROGRESS] Stage {stage}/{total} completed: {message}"
        if self.verbose:
            print(line)
        if self.progress_callback:
            self.progress_callback(line)

    def timing(self, stage: str, start: float) -> None:
        line = f"[TIMING] {stage}: {time.perf_counter() - start:.3f} seconds"
        if self.verbose:
            print(line)
        if self.progress_callback:
            self.progress_callback(line)

    def total(self) -> None:
        line = f"[TIMING] Total execution: {time.perf_counter() - self._total_start:.3f} seconds"
        if self.verbose:
            print(line)
        if self.progress_callback:
            self.progress_callback(line)


class LRUCache:
    def __init__(self, maxsize: int = 50) -> None:
        self.maxsize = maxsize
        self._data: OrderedDict[str, Command] = OrderedDict()

    def get(self, key: str) -> Command | None:
        if key not in self._data:
            return None
        self._data.move_to_end(key)
        return _copy_command(self._data[key])

    def put(self, key: str, value: Command) -> None:
        self._data[key] = _copy_command(value)
        self._data.move_to_end(key)
        if len(self._data) > self.maxsize:
            self._data.popitem(last=False)

    def __len__(self) -> int:
        return len(self._data)


class SpeedContext:
    def __init__(self, default_speed: int = 150) -> None:
        self.current_speed = default_speed
        self.last_command: Command | None = None
        self.history: deque[Command] = deque(maxlen=5)

    def adjust_speed(self, delta: int) -> int:
        self.current_speed = _clamp(self.current_speed + delta, 0, 255)
        return self.current_speed

    def remember(self, command: Command) -> None:
        command = _copy_command(command)
        if command.get("cmd") in {"MOVE", "TURN"} and "speed" in command:
            self.current_speed = _clamp(int(command["speed"]), 0, 255)
        self.last_command = command
        self.history.append(command)


class RuleMatcher:
    """Fast deterministic command layer used before llama.cpp inference."""

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
            "back up": {"cmd": "MOVE", "dir": "BACKWARD", "speed": 100, "time_ms": 500},
            "retreat a little": {"cmd": "MOVE", "dir": "BACKWARD", "speed": 100, "time_ms": 500},
            "back away from the obstacle": {"cmd": "MOVE", "dir": "BACKWARD", "speed": 100, "time_ms": 500},
            "turn left": {"cmd": "TURN", "dir": "LEFT", "speed": 120, "time_ms": 500},
            "spin left": {"cmd": "TURN", "dir": "LEFT", "speed": 120, "time_ms": 700},
            "rotate left": {"cmd": "TURN", "dir": "LEFT", "speed": 120, "time_ms": 500},
            "pivot toward the left side": {"cmd": "TURN", "dir": "LEFT", "speed": 120, "time_ms": 700},
            "turn right": {"cmd": "TURN", "dir": "RIGHT", "speed": 120, "time_ms": 500},
            "spin right": {"cmd": "TURN", "dir": "RIGHT", "speed": 120, "time_ms": 700},
            "rotate right": {"cmd": "TURN", "dir": "RIGHT", "speed": 120, "time_ms": 500},
            "face the right wall": {"cmd": "TURN", "dir": "RIGHT", "speed": 120, "time_ms": 700},
            "halt": {"cmd": "STOP", "dir": "STOP", "speed": 0, "time_ms": 0},
            "freeze": {"cmd": "STOP", "dir": "STOP", "speed": 0, "time_ms": 0},
            "stop": {"cmd": "STOP", "dir": "STOP", "speed": 0, "time_ms": 0},
            "emergency stop": {"cmd": "STOP", "dir": "STOP", "speed": 0, "time_ms": 0},
            "abort": {"cmd": "STOP", "dir": "STOP", "speed": 0, "time_ms": 0},
            "stay exactly where you are": {"cmd": "STOP", "dir": "STOP", "speed": 0, "time_ms": 0},
            "cancel movement immediately": {"cmd": "STOP", "dir": "STOP", "speed": 0, "time_ms": 0},
            "tien len": {"cmd": "MOVE", "dir": "FORWARD", "speed": 150, "time_ms": 500},
            "di thang": {"cmd": "MOVE", "dir": "FORWARD", "speed": 150, "time_ms": 500},
            "chay thang": {"cmd": "MOVE", "dir": "FORWARD", "speed": 150, "time_ms": 500},
            "lui lai": {"cmd": "MOVE", "dir": "BACKWARD", "speed": 100, "time_ms": 500},
            "di lui": {"cmd": "MOVE", "dir": "BACKWARD", "speed": 100, "time_ms": 500},
            "xoay trai": {"cmd": "TURN", "dir": "LEFT", "speed": 120, "time_ms": 500},
            "re trai": {"cmd": "TURN", "dir": "LEFT", "speed": 120, "time_ms": 500},
            "xoay phai": {"cmd": "TURN", "dir": "RIGHT", "speed": 120, "time_ms": 500},
            "re phai": {"cmd": "TURN", "dir": "RIGHT", "speed": 120, "time_ms": 500},
            "dung lai": {"cmd": "STOP", "dir": "STOP", "speed": 0, "time_ms": 0},
            "dung": {"cmd": "STOP", "dir": "STOP", "speed": 0, "time_ms": 0},
        }
        self.dynamic_exact = {
            "faster": 50,
            "speed up": 50,
            "quicker": 50,
            "increase your pace": 50,
            "nhanh hon": 50,
            "slow down": -30,
            "slower": -30,
            "decelerate": -30,
            "reduce your pace": -30,
            "cham lai": -30,
        }
        self.regex_rules: list[tuple[re.Pattern[str], Command]] = [
            (re.compile(r"\b(go|move|drive|run|head|roll)\s+(ahead|forward|forwards|straight)\b|\badvance\b"),
             {"cmd": "MOVE", "dir": "FORWARD", "speed": 150, "time_ms": 500}),
            (re.compile(r"\b(go|move|drive)\s+(back|backward|backwards)\b|\breverse\b|\bback up\b|\bretreat\b|\bback away\b"),
             {"cmd": "MOVE", "dir": "BACKWARD", "speed": 100, "time_ms": 500}),
            (re.compile(r"\b(turn|spin|rotate)\s+(left)\b|\bpivot\b.*\bleft\b"),
             {"cmd": "TURN", "dir": "LEFT", "speed": 120, "time_ms": 500}),
            (re.compile(r"\b(turn|spin|rotate)\s+(right)\b|\b(face|pivot)\b.*\bright\b"),
             {"cmd": "TURN", "dir": "RIGHT", "speed": 120, "time_ms": 500}),
            (re.compile(r"\b(stop|halt|freeze|pause|wait|hold|abort|stay|cancel)\b"),
             {"cmd": "STOP", "dir": "STOP", "speed": 0, "time_ms": 0}),
        ]
        self.dynamic_patterns: list[tuple[re.Pattern[str], int]] = [
            (re.compile(r"\b(faster|speed up|accelerate|quicker|increase.*pace|nhanh hon)\b"), 50),
            (re.compile(r"\b(slow down|slower|decelerate|reduce speed|reduce.*pace|cham lai)\b"), -30),
        ]

    def match(self, normalized_text: str) -> Command | None:
        if normalized_text in self.dynamic_exact:
            return self._speed_command(self.dynamic_exact[normalized_text])

        hit = self.exact_rules.get(normalized_text)
        if hit:
            return _copy_command(hit)

        for pattern, delta in self.dynamic_patterns:
            if pattern.search(normalized_text):
                return self._speed_command(delta)

        for pattern, command in self.regex_rules:
            if pattern.search(normalized_text):
                result = _copy_command(command)
                if result["cmd"] == "TURN" and normalized_text.startswith("spin"):
                    result["time_ms"] = max(int(result["time_ms"]), 700)
                return result
        return None

    def _speed_command(self, delta: int) -> Command:
        return {
            "cmd": "MOVE",
            "dir": "FORWARD",
            "speed": self.speed_context.adjust_speed(delta),
            "time_ms": 300,
        }


class OptimizedRobotPipeline:
    """Hierarchical Pi 4 command pipeline with fast rules and llama.cpp fallback."""

    llama_params = {
        "n_ctx": 512,
        "n_batch": 512,
        "n_threads": 4,
        "n_predict": 64,
        "temperature": 0.1,
        "top_k": 40,
        "top_p": 0.9,
        "repeat_penalty": 1.0,
        "mirostat": 2,
        "mirostat_tau": 5.0,
        "mirostat_eta": 0.1,
        "use_mmap": True,
    }

    system_prompt = (
        "You are a robot command parser. Output ONLY one minified JSON object.\n"
        'Schema: {"cmd":"MOVE|TURN|STOP","dir":"FORWARD|BACKWARD|LEFT|RIGHT|STOP",'
        '"speed":0-255,"time_ms":0-5000}\n'
        'Examples: advance={"cmd":"MOVE","dir":"FORWARD","speed":150,"time_ms":500}; '
        'retreat={"cmd":"MOVE","dir":"BACKWARD","speed":100,"time_ms":500}; '
        'pivot left={"cmd":"TURN","dir":"LEFT","speed":120,"time_ms":700}; '
        'stay={"cmd":"STOP","dir":"STOP","speed":0,"time_ms":0}.\n'
        "No markdown. No explanation. BACKWARD must use speed greater than zero."
    )

    def __init__(
        self,
        model_path: str | None = None,
        progress_callback: ProgressCallback | None = None,
        cache_size: int = 50,
    ) -> None:
        self.settings = Settings()
        self.model_path = model_path or self.settings.ai_model_path
        self.progress_callback = progress_callback
        self.speed_context = SpeedContext(default_speed=150)
        self.rule_matcher = RuleMatcher(self.speed_context)
        self.cache = LRUCache(maxsize=cache_size)
        self._llm = None
        self._llm_call_parameters: set[str] | None = None

    def process(self, text: str, verbose: bool = False) -> Command:
        timer = Timer(verbose=verbose, progress_callback=self.progress_callback)
        normalized = normalize_text(text)

        start = time.perf_counter()
        command = self.rule_matcher.match(normalized)
        timer.timing("Pre-validation rules", start)
        timer.progress(1, 6, "Checking deterministic rules...")
        if command is not None:
            return self._finish(command, timer)

        start = time.perf_counter()
        cached = self.cache.get(normalized)
        timer.timing("LRU cache lookup", start)
        timer.progress(2, 6, "Checking recent command cache...")
        if cached is not None:
            return self._finish(cached, timer)

        start = time.perf_counter()
        prompt = self.build_prompt(text)
        timer.timing("ChatML prompt building", start)
        timer.progress(3, 6, "Building prompt...")

        start = time.perf_counter()
        raw_output = self.run_llama(prompt)
        timer.timing("llama.cpp inference", start)
        timer.progress(4, 6, "Running llama.cpp inference...")

        start = time.perf_counter()
        parsed = self.parse_json(raw_output)
        timer.timing("JSON parsing", start)
        timer.progress(5, 6, "Parsing model JSON...")

        start = time.perf_counter()
        command = self.validate_or_fallback(parsed, normalized)
        timer.timing("Validation", start)
        timer.progress(6, 6, "Validating command...")

        if command.get("cmd") != "MOVE" or command.get("time_ms") != 300:
            self.cache.put(normalized, command)
        return self._finish(command, timer)

    def resolve(self, text: str, verbose: bool = False) -> tuple[Command | None, float]:
        command = self.process(text, verbose=verbose)
        confidence = 1.0 if command["cmd"] != "UNKNOWN" else 0.0
        return (None if command["cmd"] == "UNKNOWN" else command), confidence

    def build_prompt(self, command: str) -> str:
        recent = list(self.speed_context.history)[-5:]
        context = json.dumps(recent, separators=(",", ":")) if recent else "[]"
        return (
            f"<|im_start|>system\n{self.system_prompt}\n"
            f"Recent commands: {context}\n<|im_end|>\n"
            f"<|im_start|>user\n{command}\n<|im_end|>\n"
            "<|im_start|>assistant\n"
        )

    def load(self) -> bool:
        if self._llm is not None:
            return True
        model_file = Path(self.model_path)
        if not model_file.exists():
            return False
        try:
            from llama_cpp import Llama
        except ImportError:
            return False

        self._llm = Llama(
            model_path=str(model_file),
            n_ctx=self.llama_params["n_ctx"],
            n_batch=self.llama_params["n_batch"],
            n_threads=self.llama_params["n_threads"],
            use_mmap=self.llama_params["use_mmap"],
            verbose=False,
        )
        return True

    def unload(self) -> None:
        self._llm = None

    def run_llama(self, prompt: str) -> str:
        if not self.load():
            return ""
        kwargs = {
            "max_tokens": self.llama_params["n_predict"],
            "temperature": self.llama_params["temperature"],
            "top_k": self.llama_params["top_k"],
            "top_p": self.llama_params["top_p"],
            "repeat_penalty": self.llama_params["repeat_penalty"],
            "mirostat_mode": self.llama_params["mirostat"],
            "mirostat_tau": self.llama_params["mirostat_tau"],
            "mirostat_eta": self.llama_params["mirostat_eta"],
            "stop": ["<|im_end|>", "\n\n"],
            "echo": False,
        }
        result = self._llm(prompt, **self._supported_llm_kwargs(kwargs))
        return str(result["choices"][0]["text"]).strip()

    def _supported_llm_kwargs(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        if self._llm_call_parameters is None:
            self._llm_call_parameters = set(signature(self._llm.__call__).parameters)
        return {key: value for key, value in kwargs.items() if key in self._llm_call_parameters}

    def parse_json(self, raw_output: str) -> Command | None:
        if not raw_output:
            return None
        start = raw_output.find("{")
        end = raw_output.rfind("}") + 1
        if start < 0 or end <= start:
            return self._parse_text_output(raw_output)
        fragment = raw_output[start:end]
        try:
            parsed = json.loads(fragment)
        except json.JSONDecodeError:
            try:
                parsed = ast.literal_eval(fragment)
            except (SyntaxError, ValueError):
                return self._parse_text_output(raw_output)
        return parsed if isinstance(parsed, dict) else None

    def _parse_text_output(self, raw_output: str) -> Command | None:
        text = normalize_text(raw_output)
        if "stop" in text or "halt" in text or "freeze" in text:
            return {"cmd": "STOP", "dir": "STOP", "speed": 0, "time_ms": 0}
        if "turn" in text or "rotate" in text or "pivot" in text:
            if "left" in text:
                return {"cmd": "TURN", "dir": "LEFT", "speed": 120, "time_ms": 700}
            if "right" in text:
                return {"cmd": "TURN", "dir": "RIGHT", "speed": 120, "time_ms": 700}
        if "backward" in text or "back" in text or "reverse" in text or "retreat" in text:
            return {"cmd": "MOVE", "dir": "BACKWARD", "speed": 100, "time_ms": 500}
        if "forward" in text or "ahead" in text or "advance" in text or text == "move":
            return {"cmd": "MOVE", "dir": "FORWARD", "speed": 150, "time_ms": 500}
        return None

    def validate_or_fallback(self, command: Command | None, normalized_text: str) -> Command:
        if command is None:
            fallback = self.rule_matcher.match(normalized_text)
            return fallback or {"cmd": "STOP", "dir": "STOP", "speed": 0, "time_ms": 0}

        cmd = str(command.get("cmd", "")).upper()
        if not cmd:
            cmd = str(command.get("command", "")).upper()
        direction = str(command.get("dir", "")).upper()
        if not direction:
            direction = str(command.get("direction", "")).upper()

        if cmd == "MOVE" and not direction:
            if any(key in command for key in ("distance", "duration", "meters")):
                direction = "FORWARD"

        if cmd == "SPEED" and direction == "STOP":
            return {"cmd": "STOP", "dir": "STOP", "speed": 0, "time_ms": 0}

        if cmd == "STOP":
            return {"cmd": "STOP", "dir": "STOP", "speed": 0, "time_ms": 0}

        if cmd == "MOVE":
            if direction not in {"FORWARD", "BACKWARD"}:
                return {"cmd": "STOP", "dir": "STOP", "speed": 0, "time_ms": 0}
            speed = _clamp(int(command.get("speed", 150)), 1, 255)
            if direction == "BACKWARD" and speed == 0:
                speed = 100
            return {
                "cmd": "MOVE",
                "dir": direction,
                "speed": speed,
                "time_ms": _clamp(int(command.get("time_ms", 500)), 100, 5000),
            }

        if cmd == "TURN":
            if direction not in {"LEFT", "RIGHT"}:
                return {"cmd": "STOP", "dir": "STOP", "speed": 0, "time_ms": 0}
            return {
                "cmd": "TURN",
                "dir": direction,
                "speed": _clamp(int(command.get("speed", 120)), 1, 255),
                "time_ms": max(_clamp(int(command.get("time_ms", 500)), 100, 5000), 500),
            }

        return {"cmd": "STOP", "dir": "STOP", "speed": 0, "time_ms": 0}

    def cache_stats(self) -> dict[str, Any]:
        return {
            "cached_phrases": len(self.cache),
            "current_speed": self.speed_context.current_speed,
            "history_size": len(self.speed_context.history),
        }

    def _finish(self, command: Command, timer: Timer) -> Command:
        command = self.validate_or_fallback(command, "")
        self.speed_context.remember(command)
        timer.total()
        return command


def benchmark() -> None:
    pipeline = OptimizedRobotPipeline()
    commands = [
        "go ahead",
        "go back",
        "reverse",
        "halt",
        "freeze",
        "faster",
        "slow down",
        "spin left",
        "spin right",
        "tien len",
        "dung lai",
    ]
    for text in commands:
        start = time.perf_counter()
        result = pipeline.process(text)
        elapsed_ms = (time.perf_counter() - start) * 1000
        print(f"{text!r} -> {result} ({elapsed_ms:.2f} ms)")


if __name__ == "__main__":
    benchmark()
