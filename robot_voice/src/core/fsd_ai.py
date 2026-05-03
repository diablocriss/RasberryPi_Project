import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from pathlib import Path
from typing import Any

from config.settings import Settings
from core.tasx_adapter import adapt_tasx_output, validate_command

Command = dict[str, Any]


class TASXResolver:
    def __init__(self, model_path: str, n_ctx: int = 256, n_threads: int = 2) -> None:
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self.settings = Settings()
        self._llm = None
        self._executor = ThreadPoolExecutor(max_workers=1)

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
            n_ctx=self.n_ctx,
            n_threads=self.n_threads,
            verbose=False,
        )
        return True

    def resolve(self, text: str) -> tuple[Command | None, float]:
        if not text.strip() or not self.load():
            return None, 0.0

        future = self._executor.submit(self._generate, self._build_prompt(text))
        try:
            raw = future.result(timeout=self.settings.ai_timeout_ms / 1000)
        except (TimeoutError, Exception):
            return None, 0.0

        return self._parse_response(raw)

    _SYSTEM = (
        "You are a robot motor command parser. "
        "Convert natural language into a JSON object with an \"actions\" array. "
        "Each action has: cmd (MOVE|TURN|STOP|SPEED), "
        "dir (FORWARD|BACKWARD|LEFT|RIGHT, omit for STOP/SPEED), "
        "speed (0-255, optional), time_ms (100-5000, optional). "
        "Output ONLY the JSON object, no explanation."
    )

    def _build_prompt(self, text: str) -> str:
        return (
            f"<|im_start|>system\n{self._SYSTEM}<|im_end|>\n"
            f"<|im_start|>user\n{text.strip()}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )

    def _parse_response(self, raw: str) -> tuple[Command | None, float]:
        try:
            payload = json.loads(self._extract_json(raw))
        except json.JSONDecodeError:
            return None, 0.0

        actions = payload.get("actions") if isinstance(payload, dict) else payload
        if not isinstance(actions, list):
            return None, 0.0

        command = adapt_tasx_output(actions)
        if not command or not validate_command(command):
            return None, 0.0

        return command, 0.9

    def unload(self) -> None:
        self._llm = None
        self._executor.shutdown(wait=False)
        self._executor = ThreadPoolExecutor(max_workers=1)

    def _generate(self, prompt: str) -> str:
        result = self._llm(
            prompt,
            max_tokens=150,
            temperature=0,
            stop=["<|im_end|>"],
            echo=False,
        )
        return result["choices"][0]["text"].strip()

    def _extract_json(self, raw: str) -> str:
        stripped = raw.strip()
        array_start = stripped.find("[")
        object_start = stripped.find("{")
        starts = [pos for pos in (array_start, object_start) if pos >= 0]
        if not starts:
            return stripped
        start = min(starts)
        end_char = "]" if stripped[start] == "[" else "}"
        end = stripped.rfind(end_char)
        if end < start:
            return stripped[start:]
        return stripped[start : end + 1]
