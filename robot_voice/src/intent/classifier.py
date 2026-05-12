"""Production wrapper around the trained FastText intent classifier.

Designed to plug into the MoonShine voice pipeline (src/core/response_handler.py
and src/audio/pipeline_moonshine.py). Keeps the same preprocessing pipeline
that train.py used.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Iterable

try:
    import fasttext
    import numpy as _np
except ImportError as e:  # pragma: no cover - import error surfaced at runtime
    fasttext = None  # type: ignore[assignment]
    _IMPORT_ERROR: Exception | None = e
else:
    _IMPORT_ERROR = None

    # fasttext 0.9.2 calls `np.array(probs, copy=False)` which numpy 2.x
    # rejects (ValueError "Unable to avoid copy while creating an array").
    # Replace .predict with a version that uses np.asarray instead. On numpy<2
    # the behaviour is identical; on numpy>=2 this lets us run without
    # downgrading numpy across the rest of the pipeline (MoonShine etc.).
    # The C binding returns (prob, label) tuples; text must end with '\n'.
    def _patched_predict(self, text, k=1, threshold=0.0, on_unicode_error="strict"):
        def _check(entry: str) -> str:
            if "\n" in entry:
                raise ValueError(
                    "predict processes one line at a time (remove '\\n')"
                )
            return entry + "\n"

        if isinstance(text, list):
            text = [_check(t) for t in text]
            return self.f.multilinePredict(text, k, threshold, on_unicode_error)
        line = _check(text)
        predictions = self.f.predict(line, k, threshold, on_unicode_error)
        if predictions:
            probs, labels = zip(*predictions)
        else:
            probs, labels = ((), ())
        return labels, _np.asarray(probs)

    fasttext.FastText._FastText.predict = _patched_predict

try:
    from .preprocess import preprocess
except ImportError:  # running as a top-level module
    from preprocess import preprocess  # type: ignore

LABEL_PREFIX = "__label__"
# Project layout: robot_voice/src/intent/classifier.py and robot_voice/models/...
DEFAULT_MODEL = (
    Path(__file__).resolve().parent.parent.parent / "models" / "hotel_reception_intent.bin"
)

logger = logging.getLogger(__name__)


class IntentClassifier:
    """FastText-backed intent classifier with confidence-threshold fallback."""

    UNKNOWN_INTENT = "unknown"
    MIN_INPUT_LEN = 1  # characters after preprocessing

    def __init__(
        self,
        model_path: str | Path | None = None,
        confidence_threshold: float = 0.5,
        low_conf_log_threshold: float | None = None,
        watch: bool = False,
    ) -> None:
        if fasttext is None:
            raise RuntimeError(
                "fasttext is not installed. Install with `pip install fasttext-wheel`."
            ) from _IMPORT_ERROR

        path = Path(model_path) if model_path else DEFAULT_MODEL
        if not path.exists():
            raise FileNotFoundError(
                f"Intent model not found at {path}. Run `python -m src.intent.train` first."
            )

        self.model_path = path
        self.confidence_threshold = float(confidence_threshold)
        # By default warn on anything that *passed* the threshold by less than 10 points.
        self.low_conf_log_threshold = (
            float(low_conf_log_threshold)
            if low_conf_log_threshold is not None
            else self.confidence_threshold + 0.1
        )
        self._model = fasttext.load_model(str(path))
        self._model_lock = threading.Lock()
        self._labels: list[str] = sorted(
            lbl.replace(LABEL_PREFIX, "") for lbl in self._model.get_labels()
        )
        self._mtime = os.path.getmtime(str(path))

        if watch:
            self._watcher = threading.Thread(
                target=self._watch, daemon=True, name="ClassifierWatcher"
            )
            self._watcher.start()

    def _watch(self) -> None:
        """Poll model file every 2 s; reload on mtime change (hot-reload)."""
        while True:
            time.sleep(2)
            try:
                mtime = os.path.getmtime(str(self.model_path))
                if mtime != self._mtime:
                    new_model = fasttext.load_model(str(self.model_path))
                    new_labels = sorted(
                        lbl.replace(LABEL_PREFIX, "") for lbl in new_model.get_labels()
                    )
                    with self._model_lock:
                        self._model = new_model
                        self._labels = new_labels
                        self._mtime = mtime
                    logger.info("IntentClassifier: model hot-reloaded from %s", self.model_path)
            except Exception as exc:
                logger.error("IntentClassifier hot-reload error: %s", exc)

    @property
    def labels(self) -> list[str]:
        return list(self._labels)

    def predict(self, text: str) -> dict[str, Any]:
        cleaned = preprocess(text or "")
        if len(cleaned) < self.MIN_INPUT_LEN:
            return {
                "intent": self.UNKNOWN_INTENT,
                "confidence": 0.0,
                "all_scores": {},
                "raw_text": text,
                "cleaned_text": cleaned,
                "below_threshold": True,
            }

        # Ask the model for every label so callers can inspect the full distribution.
        with self._model_lock:
            k = len(self._labels) or -1
            labels, probs = self._model.predict(cleaned, k=k)
        all_scores = {
            lbl.replace(LABEL_PREFIX, ""): float(p) for lbl, p in zip(labels, probs)
        }
        top_intent = labels[0].replace(LABEL_PREFIX, "")
        top_conf = float(probs[0])

        below = top_conf < self.confidence_threshold
        if below:
            logger.info(
                "intent below threshold: '%s' -> %s (%.2f < %.2f) -> unknown",
                cleaned, top_intent, top_conf, self.confidence_threshold,
            )
        elif top_conf < self.low_conf_log_threshold:
            logger.debug(
                "low-confidence intent: '%s' -> %s (%.2f)",
                cleaned, top_intent, top_conf,
            )

        return {
            "intent": self.UNKNOWN_INTENT if below else top_intent,
            "confidence": top_conf,
            "all_scores": all_scores,
            "raw_text": text,
            "cleaned_text": cleaned,
            "below_threshold": below,
        }

    def batch_predict(self, texts: Iterable[str]) -> list[dict[str, Any]]:
        return [self.predict(t) for t in texts]
