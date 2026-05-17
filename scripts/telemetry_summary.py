"""
Reads static/telemetry.jsonl and prints per-(provider, model, op) stats:
calls, success rate, P50 / P95 latency, total tokens, estimated $.

Run from project root:
    venv\\Scripts\\python.exe scripts\\telemetry_summary.py
    venv\\Scripts\\python.exe scripts\\telemetry_summary.py --since 24h
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
from telemetry import PRICING, _LOG_PATH  # noqa: E402


def _parse_since(s: str | None) -> float:
    if not s:
        return 0.0
    unit = s[-1]
    n = float(s[:-1])
    mult = {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]
    return time.time() - n * mult


def _percentile(vals: list[float], p: float) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    k = max(0, min(len(s) - 1, int(round(p / 100 * (len(s) - 1)))))
    return s[k]


def _cost(provider: str, model: str, prompt_t: int, completion_t: int,
          n_calls: int) -> float:
    price = PRICING.get((provider, model))
    if not price:
        return 0.0
    in_per_1m, out_per_1m = price
    # special-case image: out_per_1m is $/image when model id ends with -image
    if model.endswith("-image"):
        return n_calls * (out_per_1m / 1000)
    return prompt_t / 1_000_000 * in_per_1m + completion_t / 1_000_000 * out_per_1m


def load(since_ts: float) -> list[dict]:
    if not os.path.exists(_LOG_PATH):
        return []
    out: list[dict] = []
    with open(_LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except Exception:
                continue
            if ev.get("ts", 0) >= since_ts:
                out.append(ev)
    return out


def summarise(events: list[dict]) -> dict:
    buckets: dict[tuple, list[dict]] = defaultdict(list)
    for ev in events:
        key = (ev.get("provider"), ev.get("model"), ev.get("op"))
        buckets[key].append(ev)

    rows = []
    for (prov, model, op), evs in sorted(buckets.items()):
        latencies = [e.get("latency_ms", 0.0) for e in evs]
        successes = sum(1 for e in evs if e.get("success"))
        prompt_t = sum(int(e.get("prompt_tokens", 0) or 0) for e in evs)
        comp_t = sum(int(e.get("completion_tokens", 0) or 0) for e in evs)
        rows.append({
            "provider": prov, "model": model, "op": op,
            "calls": len(evs),
            "success_rate": successes / len(evs) if evs else 0.0,
            "p50_ms": round(_percentile(latencies, 50), 1),
            "p95_ms": round(_percentile(latencies, 95), 1),
            "avg_ms": round(sum(latencies) / len(latencies), 1) if latencies else 0,
            "prompt_tokens": prompt_t,
            "completion_tokens": comp_t,
            "est_usd": round(_cost(prov, model, prompt_t, comp_t, len(evs)), 5),
        })
    return {"rows": rows, "n_events": len(events)}


def print_table(summary: dict) -> None:
    rows = summary["rows"]
    if not rows:
        print("(no events)")
        return
    print(f"=== Telemetry summary ({summary['n_events']} events) ===")
    print()
    headers = ["provider", "model", "op", "calls", "ok%", "p50ms", "p95ms",
               "in_tok", "out_tok", "$"]
    widths = [8, 28, 18, 5, 5, 7, 7, 8, 8, 9]
    print("| " + " | ".join(h.ljust(w) for h, w in zip(headers, widths)) + " |")
    print("|" + "|".join("-" * (w + 2) for w in widths) + "|")
    for r in rows:
        vals = [
            r["provider"] or "?",
            (r["model"] or "?")[:28],
            (r["op"] or "?")[:18],
            str(r["calls"]),
            f"{r['success_rate'] * 100:.0f}",
            f"{r['p50_ms']:.0f}",
            f"{r['p95_ms']:.0f}",
            str(r["prompt_tokens"]),
            str(r["completion_tokens"]),
            f"${r['est_usd']:.4f}",
        ]
        print("| " + " | ".join(str(v).ljust(w) for v, w in zip(vals, widths)) + " |")

    total_cost = sum(r["est_usd"] for r in rows)
    total_calls = sum(r["calls"] for r in rows)
    print()
    print(f"Total spend (est): ${total_cost:.4f} across {total_calls} calls.")
    # Per-meme estimate if 'judge_captions' is the canonical end-of-pipeline marker
    meme_count = sum(r["calls"] for r in rows if r["op"] == "judge_captions")
    if meme_count:
        per_meme = total_cost / meme_count
        print(f"~{meme_count} memes generated  →  ${per_meme * 1000:.2f} per 1000 memes "
              f"(${per_meme:.5f} each).")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--since", default=None,
                   help="Only include events from the last N (e.g. 24h, 30m, 7d).")
    args = p.parse_args()
    since_ts = _parse_since(args.since)
    events = load(since_ts)
    print_table(summarise(events))


if __name__ == "__main__":
    main()
