from dataclasses import dataclass


@dataclass(frozen=True)
class AISettings:
    ai_enabled: bool = True
    ai_model_type: str = "tasx"
    ai_model_path: str = "models/tasx-cmd-0.5b-q4_k_m.gguf"
    ai_confidence_threshold: float = 0.7
    ai_timeout_ms: int = 800
    ai_context_history: int = 10
