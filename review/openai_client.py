"""Egyetlen Responses API-hívás (POST /v1/responses), újrapróbálkozás NÉLKÜL (költségvédelem).

A kulcs csak a kérés fejlécébe kerül; a fejlécet, a kérést és a kulcsot soha nem naplózzuk.
"""

import json
import urllib.error
import urllib.request

from review import config
from review.redact import redact

API_URL = "https://api.openai.com/v1/responses"


class ApiError(Exception):
    def __init__(self, kind, http_status=None, detail=""):
        super().__init__(kind)
        self.kind = kind
        self.http_status = http_status
        self.detail = redact(detail)[:300]


def _error_detail(body):
    try:
        err = json.loads(body).get("error") or {}
        return f"{err.get('type') or ''} {err.get('code') or ''}".strip()
    except Exception:
        return ""


def call(payload, api_key, opener=None):
    if not api_key:
        raise ApiError("NO_API_KEY")
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    open_fn = opener or urllib.request.urlopen
    try:
        with open_fn(req, timeout=config.REQUEST_TIMEOUT_S) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace") if hasattr(e, "read") else ""
        raise ApiError("HTTP_ERROR", e.code, _error_detail(body)) from None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise ApiError("NETWORK_ERROR", None, type(e).__name__) from None
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        raise ApiError("INVALID_RESPONSE_JSON") from None


def extract(response):
    """Visszaad: (output_text, usage, status). Hiányzó / hiányos válasz -> ApiError."""
    if not isinstance(response, dict):
        raise ApiError("INVALID_RESPONSE_SHAPE")
    status = response.get("status")
    usage = response.get("usage") or {}
    usage = {"input_tokens": int(usage.get("input_tokens") or 0),
             "output_tokens": int(usage.get("output_tokens") or 0)}
    if status == "incomplete":
        reason = (response.get("incomplete_details") or {}).get("reason") or ""
        raise ApiError("INCOMPLETE", None, str(reason)) from None
    if status not in (None, "completed"):
        raise ApiError("BAD_STATUS", None, str(status))
    texts = []
    for item in response.get("output") or []:
        for c in (item.get("content") or []) if isinstance(item, dict) else []:
            if isinstance(c, dict) and c.get("type") == "refusal":
                raise ApiError("REFUSAL")
            if isinstance(c, dict) and c.get("type") == "output_text":
                texts.append(c.get("text") or "")
    if not texts:
        raise ApiError("NO_OUTPUT_TEXT")
    return "".join(texts), usage, status
