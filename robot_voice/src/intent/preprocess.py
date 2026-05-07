"""Shared text preprocessing for FastText hotel-reception intent classifier.

Both training and inference must use this exact pipeline so the model sees
the same token shape it was trained on.
"""
from __future__ import annotations

import re

# Keep apostrophes inside words (O'Brien, don't); strip everything else
# that is not a letter, digit or whitespace.
_PUNCT_RE = re.compile(r"[^\w\s']", flags=re.UNICODE)
_WS_RE = re.compile(r"\s+")


def preprocess(text: str) -> str:
    if not text:
        return ""
    t = text.lower()
    t = _PUNCT_RE.sub(" ", t)
    t = _WS_RE.sub(" ", t).strip()
    return t
