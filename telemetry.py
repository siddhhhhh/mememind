"""
Lightweight provider-call telemetry.

Append one JSON line per LLM call to static/telemetry.jsonl with timing +
token counts. Use the @timed decorator or telemetry.record() directly.

Read it back with scripts/telemetry_summary.py.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

_LOG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "static", "telemetry.jsonl"
)

# Approximate $/1M-token prices (Jan 2026 public pricing — keep in sync manually).
# Used only for the summary report; recording is provider-agnostic.
PRICING = {
    # provider, model -> (in_per_1m, out_per_1m)
    ("groq", "llama-3.3-70b-versatile"): (0.59, 0.79),
    ("gemini", "gemini-2.5-flash"): (0.075, 0.30),
    ("gemini", "gemini-embedding-001"): (0.025, 0.0),
    ("gemini", "gemini-2.5-flash-image"): (0.30, 30.0),  # output billed per image
}


def record(event: dict) -> None:
    """Append one event to the JSONL log. Never raises (telemetry must not break prod)."""
    try:
        event = {"ts": time.time(), **event}
        os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, default=str) + "\n")
    except Exception:
        pass


def _extract_groq_tokens(resp: Any) -> dict:
    try:
        u = resp.usage
        return {
            "prompt_tokens": int(getattr(u, "prompt_tokens", 0) or 0),
            "completion_tokens": int(getattr(u, "completion_tokens", 0) or 0),
        }
    except Exception:
        return {"prompt_tokens": 0, "completion_tokens": 0}


def _extract_gemini_tokens(resp: Any) -> dict:
    try:
        u = resp.usage_metadata
        return {
            "prompt_tokens": int(getattr(u, "prompt_token_count", 0) or 0),
            "completion_tokens": int(getattr(u, "candidates_token_count", 0) or 0),
        }
    except Exception:
        return {"prompt_tokens": 0, "completion_tokens": 0}


class call:
    """Context manager: `with telemetry.call(provider, model, op) as t: t.set_response(resp)`."""

    def __init__(self, provider: str, model: str, op: str):
        self.provider = provider
        self.model = model
        self.op = op
        self.t0 = 0.0
        self.tokens = {"prompt_tokens": 0, "completion_tokens": 0}
        self.error: str | None = None

    def __enter__(self) -> "call":
        self.t0 = time.time()
        return self

    def set_response(self, resp: Any) -> None:
        if self.provider == "groq":
            self.tokens = _extract_groq_tokens(resp)
        elif self.provider == "gemini":
            self.tokens = _extract_gemini_tokens(resp)

    def __exit__(self, exc_type, exc, tb) -> None:
        latency_ms = (time.time() - self.t0) * 1000.0
        if exc is not None:
            self.error = f"{exc_type.__name__}: {exc}"
        record({
            "provider": self.provider,
            "model": self.model,
            "op": self.op,
            "latency_ms": round(latency_ms, 1),
            **self.tokens,
            "success": exc is None,
            "error": self.error,
        })
        # don't suppress
        return None
