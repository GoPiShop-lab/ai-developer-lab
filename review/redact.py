import os
import re

_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{8,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
]


def redact(text):
    """Titokszerű minták és a környezetben lévő kulcs értékének eltávolítása bármely kimenetből."""
    text = "" if text is None else str(text)
    secret = os.environ.get("OPENAI_API_KEY") or ""
    if len(secret) >= 8:
        text = text.replace(secret, "[REDACTED]")
    for p in _PATTERNS:
        text = p.sub("[REDACTED]", text)
    return text
