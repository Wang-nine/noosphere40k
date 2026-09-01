"""Secrets handling utilities (A-03): never log or print secret values."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

API_KEY_PATTERN = re.compile(r"(?i)(api[_-]?key|token|secret)\s*[:=]\s*[\w\-.]{8,}")


def key_fingerprint(secret: str) -> str:
    """Return a safely displayable fingerprint (no secret material)."""
    if not secret:
        return "empty"
    return f"len={len(secret)} sha256={hash(secret):016x}"


def redact_text(text: str) -> str:
    """Replace suspected key assignments in free text before logging."""
    return API_KEY_PATTERN.sub(r"\1: [REDACTED]", text)


def scan_for_keys(texts: Iterable[str]) -> int:
    """Count suspicious key-looking assignments (doctor / security sweep)."""
    return sum(1 for t in texts if API_KEY_PATTERN.search(t))


def normalize_key(secret: str) -> str:
    return unicodedata.normalize("NFKC", secret).strip()