"""
Offline retrieval eval for MemeMind.

Compares five rankers on a curated topic test set:
  - rag_reranked    : rag_hybrid top-20 -> LLM reranker (retriever + reranker pattern)
  - rag_hybrid      : cosine + emotion bonus (what app.pick_template actually does)
  - rag_only        : pure cosine over Gemini text-embedding-001 (no rules)
  - keyword_analysis: deterministic version of app.py's pick_template fallback
                      (uses Groq-extracted emotion + keywords + curated metadata)
  - keyword_naive   : raw topic tokens vs template name/emotions/use_cases
                      (no LLM analysis at all — the dumb baseline)

Metrics per ranker:
  - emotion_hit@k   : top-k contains a template whose emotions intersect expected
  - template_hit@k  : top-k contains one of ideal_templates
  - mrr_emotion     : 1 / rank of first emotion-overlap match (0 if none in top 20)

Run from project root:
    venv\\Scripts\\python.exe scripts\\eval.py
    venv\\Scripts\\python.exe scripts\\eval.py --limit 10   # smoke test
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import app  # imports the Flask app module but does not start the server

EVAL_SET_PATH = os.path.join(PROJECT_ROOT, "scripts", "eval_set.json")
ANALYSIS_CACHE = os.path.join(PROJECT_ROOT, "scripts", ".eval_analysis_cache.json")
EMBED_CACHE = os.path.join(PROJECT_ROOT, "scripts", ".eval_embed_cache.json")
RERANK_CACHE = os.path.join(PROJECT_ROOT, "scripts", ".eval_rerank_cache.json")
RESULTS_PATH = os.path.join(PROJECT_ROOT, "scripts", "eval_results.json")

K_LIST = (1, 3, 5)


# ---------------------------------------------------------------------------
# Caches — avoid re-burning Groq + Gemini quota on iterative runs.
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
        json.dump(data, f)
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# Rankers
# ---------------------------------------------------------------------------

_TOK_RE = re.compile(r"[A-Za-z]+")
_STOP = {
    "the", "a", "an", "and", "or", "but", "of", "in", "on", "at", "to", "for",
    "with", "is", "it", "this", "that", "be", "are", "was", "were", "you", "your",
    "my", "me", "i", "we", "they", "them", "their", "there", "here", "than", "then",
    "have", "has", "had", "do", "does", "did", "not", "no", "yes", "as", "by", "if",
    "so", "up", "out", "from", "about", "into", "over", "after", "before", "again",
    "just", "really", "very", "more", "much", "some", "any", "all", "one", "two",
    "im", "ive", "id", "ill", "youre", "youll", "its",
}


def _tokens(s: str) -> set[str]:
    return {t.lower() for t in _TOK_RE.findall(s or "") if len(t) > 2 and t.lower() not in _STOP}


def _template_doc(meta: dict) -> str:
    return " ".join(
        [
            meta.get("name", ""),
            " ".join(meta.get("emotions", [])),
            " ".join(meta.get("use_cases", [])),
            meta.get("caption_style", ""),
        ]
    )


def keyword_naive_rank(topic: str, pool: dict, k: int = 20) -> list[tuple[str, float]]:
    """Pure token overlap between user topic and template doc. No LLM in the loop."""
    qtoks = _tokens(topic)
    if not qtoks:
        return []
    scored: list[tuple[str, float]] = []
    for tid, meta in pool.items():
        dtoks = _tokens(_template_doc(meta))
        if not dtoks:
            continue
        overlap = len(qtoks & dtoks)
        if overlap == 0:
            continue
        # Jaccard-like: rewards overlap, penalises doc bloat slightly
        score = overlap / (len(qtoks | dtoks) ** 0.5)
        scored.append((tid, score))
    scored.sort(key=lambda x: -x[1])
    return scored[:k]


def keyword_analysis_rank(topic: str, analysis: dict, pool: dict,
                          k: int = 20) -> list[tuple[str, float]]:
    """Deterministic mirror of app.pick_template's keyword fallback path.

    Same scoring rules — minus the random jitter and source preference — so the
    fair comparison is 'what RAG adds on top of the existing analysis-aware
    baseline'.
    """
    target_emotion = (analysis.get("emotion") or "").lower()
    keywords = [k.lower() for k in analysis.get("keywords", [])]
    context = (analysis.get("cultural_context") or "").lower()
    context_words = [w for w in context.split() if len(w) > 3]

    scored: list[tuple[str, float]] = []
    for tid, meta in pool.items():
        score = 0.0
        emotions = [e.lower() for e in meta.get("emotions", [])]
        if target_emotion and target_emotion in emotions:
            score += 10
        for e in emotions:
            if any(k in e or e in k for k in keywords):
                score += 2
        for uc in meta.get("use_cases", []):
            uc_l = uc.lower()
            if any(k in uc_l for k in keywords):
                score += 3
            if any(w in uc_l for w in context_words):
                score += 1
        if score > 0:
            scored.append((tid, score))
    scored.sort(key=lambda x: -x[1])
    return scored[:k]


def _rag_sims(topic: str, analysis: dict, embed_cache: dict) -> "np.ndarray | None":
    """Compute the full sim vector (one entry per template in EMB_STORE.ids)."""
    import numpy as np

    app.EMB_STORE.load()
    if not app.EMB_STORE.is_ready():
        return None
    query_text = (
        f"Topic: {topic}. Tone: {analysis.get('tone', '')}. "
        f"Emotion: {analysis.get('emotion', '')}. "
        f"Context: {analysis.get('cultural_context', '')}. "
        f"Keywords: {', '.join(analysis.get('keywords', []))}."
    )
    cached = embed_cache.get(query_text)
    if cached:
        qv = np.asarray(cached, dtype=np.float32)
    else:
        qv = app.embed_query(query_text)
        if qv is None:
            return None
        embed_cache[query_text] = qv.tolist()
        _save_cache(EMBED_CACHE, embed_cache)
    return app.EMB_STORE.matrix @ qv


def rag_only_rank(topic: str, analysis: dict, embed_cache: dict,
                  k: int = 20) -> list[tuple[str, float]]:
    """Pure cosine — what 'RAG' alone gives you, no rules layered on."""
    import numpy as np
    sims = _rag_sims(topic, analysis, embed_cache)
    if sims is None:
        return []
    idx_sorted = np.argsort(-sims)[:k]
    return [(app.EMB_STORE.ids[i], float(sims[i])) for i in idx_sorted]


def rag_reranked_rank(topic: str, analysis: dict, pool: dict, embed_cache: dict,
                      rerank_cache: dict, k: int = 20) -> list[tuple[str, float]]:
    """rag_hybrid top-20 -> LLM reranker. Cached by (topic, candidate-id tuple)."""
    base = rag_hybrid_rank(topic, analysis, pool, embed_cache, k=20)
    if not base:
        return []
    cand_ids = tuple(tid for tid, _ in base)
    key = topic + "||" + "|".join(cand_ids)
    cached = rerank_cache.get(key)
    if cached is not None:
        # restore as (id, score) tuples
        return [(tid, float(sc)) for tid, sc in cached][:k]
    out = app.rerank_with_llm(topic, analysis, base, pool=pool, top_k=20)
    rerank_cache[key] = [[tid, sc] for tid, sc in out]
    _save_cache(RERANK_CACHE, rerank_cache)
    return out[:k]


def rag_hybrid_rank(topic: str, analysis: dict, pool: dict, embed_cache: dict,
                    k: int = 20) -> list[tuple[str, float]]:
    """Cosine + app._emotion_bonus(meta, analysis) — mirrors pick_template
    (minus the random jitter and top-5 weighted sampling)."""
    import numpy as np
    sims = _rag_sims(topic, analysis, embed_cache)
    if sims is None:
        return []
    scored: list[tuple[str, float]] = []
    for i, tid in enumerate(app.EMB_STORE.ids):
        meta = pool.get(tid)
        if not meta:
            continue
        scored.append((tid, float(sims[i]) + app._emotion_bonus(meta, analysis)))
    scored.sort(key=lambda x: -x[1])
    return scored[:k]


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def _emotions_of(tid: str, pool: dict) -> set[str]:
    return {e.lower() for e in pool.get(tid, {}).get("emotions", [])}


def evaluate_ranking(ranking: list[tuple[str, float]], case: dict,
                     pool: dict) -> dict:
    expected = {e.lower() for e in case.get("expected_emotions", [])}
    ideals = set(case.get("ideal_templates", []))

    emo_hits = {f"emotion_hit@{k}": 0 for k in K_LIST}
    tpl_hits = {f"template_hit@{k}": 0 for k in K_LIST}
    mrr = 0.0
    first_emo_rank = None

    for rank, (tid, _) in enumerate(ranking, 1):
        emo_match = bool(expected & _emotions_of(tid, pool))
        tpl_match = tid in ideals
        for kk in K_LIST:
            if rank <= kk:
                if emo_match:
                    emo_hits[f"emotion_hit@{kk}"] = 1
                if tpl_match:
                    tpl_hits[f"template_hit@{kk}"] = 1
        if emo_match and first_emo_rank is None:
            first_emo_rank = rank

    if first_emo_rank is not None:
        mrr = 1.0 / first_emo_rank

    out = {**emo_hits, **tpl_hits, "mrr_emotion": mrr,
           "first_emo_rank": first_emo_rank or 0}
    return out


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run(limit: int | None = None) -> dict:
    eval_data = json.load(open(EVAL_SET_PATH, "r", encoding="utf-8"))
    cases = eval_data["cases"]
    if limit:
        cases = cases[:limit]
    pool = app._all_templates()
    analysis_cache = _load_cache(ANALYSIS_CACHE)
    embed_cache = _load_cache(EMBED_CACHE)
    rerank_cache = _load_cache(RERANK_CACHE)

    # Warm-load the embedding store once so the timing isn't biased.
    app.EMB_STORE.load()
    print(f"[setup] templates total: {len(pool)} | "
          f"embeddings loaded: {len(app.EMB_STORE.ids)}")

    rankers = ("rag_reranked", "rag_hybrid", "rag_only",
               "keyword_analysis", "keyword_naive")
    agg = {r: {f"emotion_hit@{k}": 0 for k in K_LIST}
           | {f"template_hit@{k}": 0 for k in K_LIST}
           | {"mrr_emotion": 0.0}
           for r in rankers}

    per_case: list[dict] = []

    for i, case in enumerate(cases, 1):
        topic = case["topic"]
        # 1) topic analysis (cached)
        analysis = analysis_cache.get(topic)
        if analysis is None:
            try:
                analysis = app.analyze_topic(topic)
            except Exception as e:
                print(f"  [{i}/{len(cases)}] analyze failed: {e}")
                analysis = {"tone": "relatable", "emotion": "relatable",
                            "cultural_context": topic, "keywords": [topic]}
            analysis_cache[topic] = analysis
            _save_cache(ANALYSIS_CACHE, analysis_cache)
            time.sleep(0.2)  # be gentle with Groq

        # 2) run each ranker
        rankings = {
            "rag_reranked": rag_reranked_rank(topic, analysis, pool,
                                              embed_cache, rerank_cache, k=20),
            "rag_hybrid": rag_hybrid_rank(topic, analysis, pool, embed_cache, k=20),
            "rag_only": rag_only_rank(topic, analysis, embed_cache, k=20),
            "keyword_analysis": keyword_analysis_rank(topic, analysis, pool, k=20),
            "keyword_naive": keyword_naive_rank(topic, pool, k=20),
        }

        case_row = {"id": case["id"], "topic": topic, "analysis": analysis,
                    "rankings": {}, "metrics": {}}
        for r in rankers:
            top5 = [{"id": tid, "score": round(s, 4),
                     "name": pool.get(tid, {}).get("name", "?"),
                     "emotions": pool.get(tid, {}).get("emotions", [])}
                    for tid, s in rankings[r][:5]]
            metrics = evaluate_ranking(rankings[r], case, pool)
            case_row["rankings"][r] = top5
            case_row["metrics"][r] = metrics
            for key, val in metrics.items():
                if key == "first_emo_rank":
                    continue
                agg[r][key] = agg[r].get(key, 0) + val
        per_case.append(case_row)

        if i % 10 == 0 or i == len(cases):
            print(f"  [{i}/{len(cases)}] {case['id']}")

    # average
    n = len(cases)
    summary = {r: {k: (v / n if "mrr" in k else v / n)
                   for k, v in agg[r].items()}
               for r in rankers}

    return {
        "n_cases": n,
        "summary": summary,
        "per_case": per_case,
    }


def _pct(x: float) -> str:
    return f"{x * 100:5.1f}%"


def print_table(results: dict) -> None:
    s = results["summary"]
    n = results["n_cases"]
    print()
    print(f"=== MemeMind retrieval eval ({n} cases) ===")
    print()
    headers = ["ranker", "emo@1", "emo@3", "emo@5", "tpl@1", "tpl@3", "tpl@5", "MRR"]
    widths = [18, 7, 7, 7, 7, 7, 7, 7]
    line = "| " + " | ".join(h.ljust(w) for h, w in zip(headers, widths)) + " |"
    sep = "|" + "|".join("-" * (w + 2) for w in widths) + "|"
    print(line)
    print(sep)
    order = ("rag_reranked", "rag_hybrid", "rag_only",
             "keyword_analysis", "keyword_naive")
    for r in order:
        row = s[r]
        vals = [
            r,
            _pct(row["emotion_hit@1"]),
            _pct(row["emotion_hit@3"]),
            _pct(row["emotion_hit@5"]),
            _pct(row["template_hit@1"]),
            _pct(row["template_hit@3"]),
            _pct(row["template_hit@5"]),
            f"{row['mrr_emotion']:5.3f}",
        ]
        print("| " + " | ".join(v.ljust(w) for v, w in zip(vals, widths)) + " |")
    print()
    rr, rh, ro = s["rag_reranked"], s["rag_hybrid"], s["rag_only"]
    kn, ka = s["keyword_naive"], s["keyword_analysis"]

    def delta(a, b):
        return f"{(a - b) * 100:+.1f}pp"

    print("Headline deltas (rag_reranked = retriever + LLM reranker):")
    print(f"  emo@1   : vs naive {delta(rr['emotion_hit@1'], kn['emotion_hit@1'])}  "
          f"| vs hybrid {delta(rr['emotion_hit@1'], rh['emotion_hit@1'])}  "
          f"| vs rag_only {delta(rr['emotion_hit@1'], ro['emotion_hit@1'])}")
    print(f"  tpl@3   : vs naive {delta(rr['template_hit@3'], kn['template_hit@3'])}  "
          f"| vs hybrid {delta(rr['template_hit@3'], rh['template_hit@3'])}  "
          f"| vs rag_only {delta(rr['template_hit@3'], ro['template_hit@3'])}")
    print(f"  MRR     : vs naive {rr['mrr_emotion'] - kn['mrr_emotion']:+.3f}  "
          f"| vs hybrid {rr['mrr_emotion'] - rh['mrr_emotion']:+.3f}  "
          f"| vs rag_only {rr['mrr_emotion'] - ro['mrr_emotion']:+.3f}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None,
                        help="Only run the first N cases (smoke test).")
    parser.add_argument("--no-save", action="store_true",
                        help="Print only — don't write eval_results.json.")
    args = parser.parse_args()

    results = run(limit=args.limit)
    print_table(results)

    if not args.no_save:
        _save_cache(RESULTS_PATH, results)
        size_kb = os.path.getsize(RESULTS_PATH) / 1024
        print(f"[saved] {RESULTS_PATH} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
