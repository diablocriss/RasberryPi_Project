"""Hotel-reception response handler backed by the FastText intent classifier.

The classifier categorises the guest utterance into one of 15 intents
(see src/intent/training_data.json). Predictions below the confidence
threshold are mapped to "unknown" so the robot asks the guest to rephrase.

API contract (called from src/audio/pipeline_moonshine.py):
    handler = ResponseHandler()
    reply = handler.process(text)
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Hotel-reception response copy. Keys must match intent labels emitted by
# src/intent/classifier.py exactly.
INTENT_RESPONSES: dict[str, str] = {
    "greeting":     "Welcome to the hotel! How may I assist you?",
    "goodbye":      "Thank you for visiting. Have a wonderful day!",
    "check_in":     "I'd be happy to help you check in. May I have your name, please?",
    "check_out":    "I'll assist you with check-out. What is your room number?",
    "room_inquiry": "Let me check our room availability. What dates are you looking for?",
    "facilities":   "Our facilities include a gym, pool, and restaurant. What would you like to know?",
    "wifi":         "Our WiFi network is 'HotelGuest'. The password is 'stayhappy2024'.",
    "directions":   "Let me help you find your way. Where would you like to go?",
    "complaint":    "I'm sorry to hear that. Let me notify our staff to assist you immediately.",
    "concierge":    "I'd love to help with recommendations. What are you interested in?",
    "confirm_yes":  "Great, let me proceed with that.",
    "confirm_no":   "Alright, let me know if you need anything else.",
    "identity":     "Thank you. Let me pull up your information.",
    "thanks":       "You're welcome! Is there anything else I can help with?",
    "unknown":      "I apologize, I didn't quite understand. Could you please rephrase that?",
}

EMPTY_INPUT_REPLY = "I didn't hear anything. Please try again."


class ResponseHandler:
    """Maps a transcribed guest utterance to a robot reply via FastText."""

    def __init__(
        self,
        model_path: str | Path | None = None,
        confidence_threshold: float = 0.5,
    ) -> None:
        # Lazy import keeps fasttext out of import paths that don't need it
        # (e.g. the wake_word smoke tests in scripts/).
        try:
            from intent.classifier import IntentClassifier
        except ModuleNotFoundError:
            from src.intent.classifier import IntentClassifier  # type: ignore

        self._classifier = IntentClassifier(
            model_path=model_path,
            confidence_threshold=confidence_threshold,
        )

        # Sanity check: every intent the model can emit must have a reply.
        missing = [lbl for lbl in self._classifier.labels if lbl not in INTENT_RESPONSES]
        if missing:
            raise RuntimeError(
                f"INTENT_RESPONSES is missing replies for: {missing}"
            )

    def process(self, text: str) -> str:
        if not text or not text.strip():
            return EMPTY_INPUT_REPLY

        result = self._classifier.predict(text)
        intent = result["intent"]
        conf = result["confidence"]

        logger.info(
            "\033[36mINTENT %s @ %.2f for %r\033[0m",
            intent, conf, text,
        )

        # IntentClassifier already maps below-threshold predictions to
        # "unknown", so a straight dict lookup is enough.
        return INTENT_RESPONSES.get(intent, INTENT_RESPONSES["unknown"])
