"""
A/B test for the caption-writing prompt.

For each topic in scripts/eval_set.json (subset):
  1. Pick the template via the production retrieval path.
  2. Generate N candidates with prompt variant A (control = current production prompt).
  3. Generate N candidates with prompt variant B (treatment = more specific guidance).
  4. Pool both sets of candidates and judge them in a SINGLE judge call so the
     scorer sees them side-by-side (controls for judge-baseline drift).
  5. Aggregate mean humor / relevance / fit / overall per variant.

Result tells you whether B beats A on the same retrieval pool and the same judge.

Run from project root:
    venv\\Scripts\\python.exe scripts\\prompt_ab.py
    venv\\Scripts\\python.exe scripts\\prompt_ab.py --limit 10 --n 4
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import app  # reuse Groq client, retrieval, judge

EVAL_SET_PATH = os.path.join(PROJECT_ROOT, "scripts", "eval_set.json")
ANALYSIS_CACHE = os.path.join(PROJECT_ROOT, "scripts", ".eval_analysis_cache.json")
RESULTS_PATH = os.path.join(PROJECT_ROOT, "scripts", "prompt_ab_results.json")


# ---------------------------------------------------------------------------
# Prompt variants
# ---------------------------------------------------------------------------

def _common_system() -> str:
    return (
        "You write meme captions. Be funny, witty, culturally aware, and concise. "
        "Match the meme template's style. Return strict JSON only."
    )


def variant_a_user(topic: str, analysis: dict, template_meta: dict,
                   zones_desc: str, zone_ids: list[str], n: int) -> str:
    """CONTROL — current production prompt (matches app.write_captions_n)."""
    example_obj = "{" + ", ".join(f'"{zid}": "..."' for zid in zone_ids) + "}"
    return f"""Generate {n} DIFFERENT caption candidates for this meme template.

Topic: "{topic}"
Topic analysis: {json.dumps(analysis)}

Template: {template_meta.get('name')}
Style guide: {template_meta.get('caption_style')}

Each candidate must be a JSON object with EXACTLY these keys:
{zones_desc}

Each candidate object example: {example_obj}

Return JSON: {{"candidates": [<obj>, <obj>, ...]}} with exactly {n} objects.
Make them genuinely different — different jokes, not paraphrases.
No markdown, no extra commentary."""


def variant_b_user(topic: str, analysis: dict, template_meta: dict,
                   zones_desc: str, zone_ids: list[str], n: int) -> str:
    """TREATMENT — adds specificity-and-surprise guidance and explicit anti-patterns."""
    example_obj = "{" + ", ".join(f'"{zid}": "..."' for zid in zone_ids) + "}"
    return f"""Generate {n} DIFFERENT caption candidates for this meme template.

Topic: "{topic}"
Topic analysis: {json.dumps(analysis)}

Template: {template_meta.get('name')}
Style guide: {template_meta.get('caption_style')}

THINK FIRST (silently): what is the SPECIFIC absurdity, contradiction, or
surprising twist in this exact topic? The funniest caption names that twist
directly — don't restate the topic.

Strong caption traits:
  - Concrete and specific (names a real thing, time, number, or place)
  - Surprises in the second beat (subverts what the first beat sets up)
  - Sounds like something a real person would actually say

Avoid these failure modes:
  - Generic "when X happens" or "me trying to Y" framings
  - Restating the topic verbatim
  - Vague punchlines like "it's a mood" or "story of my life"
  - Forced internet slang that doesn't fit the template's vibe

Each candidate must be a JSON object with EXACTLY these keys:
{zones_desc}

Each candidate object example: {example_obj}

Return JSON: {{"candidates": [<obj>, <obj>, ...]}} with exactly {n} objects.
Make them genuinely different — different jokes, not paraphrases.
No markdown, no extra commentary."""


def generate_candidates(topic: str, analysis: dict, template_meta: dict,
                        user_prompt_fn, n: int) -> list[dict]:
    """Mirror of app.write_captions_n but with an injected prompt builder."""
    zones = template_meta.get("text_zones", [])
    zone_ids = [z["id"] for z in zones]
    zones_desc = "\n".join(
        f'- "{z["id"]}" (max ~{z["max_chars"]} chars)' for z in zones
    )
    try:
        result = app._groq_json(
            _common_system(),
            user_prompt_fn(topic, analysis, template_meta, zones_desc, zone_ids, n),
        )
        cands = result.get("candidates", []) if isinstance(result, dict) else []
    except Exception as e:
        print(f"    [groq err] {e}")
        cands = []

    cleaned: list[dict] = []
    for c in cands:
        if not isinstance(c, dict):
            continue
        extras = [v for k, v in c.items() if k not in zone_ids and v]
        out = {}
        for z in zones:
            zid = z["id"]
            v = c.get(zid)
            if not v and extras:
                v = extras.pop(0)
            out[zid] = v or ""
        if any(out.values()):
            cleaned.append(out)
    return cleaned


# ---------------------------------------------------------------------------
# Side-by-side judging
# ---------------------------------------------------------------------------

def judge_pooled(topic: str, template_meta: dict,
                 labelled_candidates: list[tuple[str, dict]]) -> list[dict]:
    """Run a SINGLE judge call over candidates from both variants pooled together.

    Input  : [(variant_label, captions_dict), ...]
    Output : [{variant, captions, humor, relevance, fit, overall}, ...]
    """
    if not labelled_candidates:
        return []
    # Shuffle so the judge can't infer ordering bias.
    indexed = list(enumerate(labelled_candidates))
    random.shuffle(indexed)
    shuffled = [(orig_i, lbl, caps) for orig_i, (lbl, caps) in indexed]

    rendered = "\n".join(
        f"  [{display_i + 1}] " + json.dumps(caps, ensure_ascii=False)
        for display_i, (_, _, caps) in enumerate(shuffled)
    )
    system = (
        "You are an expert meme critic. Judge these caption candidates for a "
        "specific meme template. Score each independently — do not anchor on "
        "the others. Return strict JSON only."
    )
    user = f"""Rate these {len(shuffled)} caption candidates for the meme template.

Topic: "{topic}"
Template: {template_meta.get('name')}
Style guide: {template_meta.get('caption_style')}

Candidates (1-indexed):
{rendered}

Score each on 0-10: humor, topic_relevance, template_fit. Compute overall as
(humor*0.5 + topic_relevance*0.25 + template_fit*0.25).

Return JSON:
{{
  "rankings": [
    {{"index": <1-based>, "humor": <0-10>, "topic_relevance": <0-10>,
      "template_fit": <0-10>, "overall": <0-10>}}
  ]
}}
Include ALL candidates. No prose."""

    try:
        result = app._groq_json(system, user, temperature=0.2)
    except Exception as e:
        print(f"    [judge err] {e}")
        return []

    by_idx = {r.get("index"): r for r in result.get("rankings", [])
              if isinstance(r, dict)}
    out: list[dict] = []
    for display_i, (orig_i, label, caps) in enumerate(shuffled):
        r = by_idx.get(display_i + 1, {})
        out.append({
            "variant": label,
            "captions": caps,
            "humor": float(r.get("humor", 0.0) or 0.0),
            "relevance": float(r.get("topic_relevance", 0.0) or 0.0),
            "fit": float(r.get("template_fit", 0.0) or 0.0),
            "overall": float(r.get("overall", 0.0) or 0.0),
        })
    return out


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def _load_cache(path: str) -> dict:
    if os.path.exists(path):
        try:
            return json.load(open(path, "r", encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_cache(path: str, data: dict) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def run(limit: int, n_per_variant: int) -> dict:
    cases = json.load(open(EVAL_SET_PATH, "r", encoding="utf-8"))["cases"][:limit]
    analysis_cache = _load_cache(ANALYSIS_CACHE)
    random.seed(42)

    per_case: list[dict] = []
    agg = {"A": [], "B": []}

    for i, case in enumerate(cases, 1):
        topic = case["topic"]
        print(f"\n[{i}/{len(cases)}] {topic[:70]}")

        analysis = analysis_cache.get(topic) or app.analyze_topic(topic)
        analysis_cache[topic] = analysis
        _save_cache(ANALYSIS_CACHE, analysis_cache)

        try:
            tid, meta = app.pick_template(analysis, topic=topic)
        except Exception as e:
            print(f"  pick_template failed: {e}")
            continue

        cands_a = generate_candidates(topic, analysis, meta, variant_a_user,
                                      n=n_per_variant)
        cands_b = generate_candidates(topic, analysis, meta, variant_b_user,
                                      n=n_per_variant)
        print(f"  template: {meta.get('name')}  |  A={len(cands_a)} B={len(cands_b)}")
        if not cands_a or not cands_b:
            print("  skip (one variant produced nothing)")
            continue

        labelled = ([("A", c) for c in cands_a]
                    + [("B", c) for c in cands_b])
        scored = judge_pooled(topic, meta, labelled)
        if not scored:
            continue

        per_case.append({
            "id": case["id"],
            "topic": topic,
            "template_id": tid,
            "template_name": meta.get("name"),
            "scored": scored,
        })
        for s in scored:
            agg[s["variant"]].append(s)
        time.sleep(0.4)  # gentle on Groq

    return {
        "n_cases": len(per_case),
        "n_per_variant": n_per_variant,
        "summary": _summarise(agg),
        "per_case": per_case,
    }


def _summarise(agg: dict) -> dict:
    out: dict[str, dict] = {}
    for v, scored in agg.items():
        n = len(scored) or 1
        out[v] = {
            "n": len(scored),
            "humor": round(sum(s["humor"] for s in scored) / n, 3),
            "relevance": round(sum(s["relevance"] for s in scored) / n, 3),
            "fit": round(sum(s["fit"] for s in scored) / n, 3),
            "overall": round(sum(s["overall"] for s in scored) / n, 3),
        }
    return out


def print_table(results: dict) -> None:
    s = results["summary"]
    print()
    print(f"=== Caption prompt A/B ({results['n_cases']} topics × "
          f"{results['n_per_variant']} candidates per variant) ===")
    print()
    print("| variant         | n    | humor | relev | fit   | overall |")
    print("|-----------------|------|-------|-------|-------|---------|")
    for v, label in (("A", "A (control)"), ("B", "B (specific+twist)")):
        r = s[v]
        print(f"| {label:<15} | {r['n']:<4} | {r['humor']:5.2f} | {r['relevance']:5.2f} |"
              f" {r['fit']:5.2f} | {r['overall']:6.2f}  |")
    a, b = s["A"], s["B"]
    print()
    print("Treatment minus control (B - A):")
    print(f"  humor   : {b['humor'] - a['humor']:+.2f}")
    print(f"  relev   : {b['relevance'] - a['relevance']:+.2f}")
    print(f"  fit     : {b['fit'] - a['fit']:+.2f}")
    print(f"  overall : {b['overall'] - a['overall']:+.2f}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=20,
                   help="How many topics to test (default 20).")
    p.add_argument("--n", type=int, default=4,
                   help="Candidates per variant per topic (default 4).")
    args = p.parse_args()

    results = run(limit=args.limit, n_per_variant=args.n)
    print_table(results)
    _save_cache(RESULTS_PATH, results)
    print(f"\n[saved] {RESULTS_PATH}")


if __name__ == "__main__":
    main()
