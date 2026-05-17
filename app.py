"""
MemeMind backend — 3-mode meme engine.

Modes
-----
SMART  : pick from local + Imgflip templates (~120+ templates), AI-write captions, render with PIL.
FRESH  : Gemini 2.5 Flash Image ("Nano Banana") generates a brand-new background image
         from the topic, then we overlay the AI caption.
UPLOAD : user POSTs an image; backend writes a caption fitted to that image and renders.

LLM stack
---------
Groq (Llama 3.3 70B) is the primary text LLM (fastest, cheapest) for analysis + captioning.
Gemini 1.5 Flash is the text fallback, and Gemini 2.5 Flash Image is the image generator.

Templates
---------
Local templates live under static/meme_templates/ with hand-curated metadata in templates_meta.json.
Imgflip templates are fetched on first use, cached to static/imgflip_cache/<id>.<ext>, with metadata
auto-derived from name + box_count and persisted to static/imgflip_meta.json.
"""

from __future__ import annotations

import io
import json
import os
import random
import threading
import time
import uuid
from typing import Any

import numpy as np
import requests
from dotenv import load_dotenv
from flask import Flask, abort, jsonify, request, send_file, url_for
from flask_cors import CORS
from PIL import Image, ImageDraw, ImageFont

import telemetry

# Optional provider SDKs — degrade gracefully if missing.
try:
    from groq import Groq
except ImportError:
    Groq = None

try:
    from google import genai as google_genai
    from google.genai import types as genai_types
except ImportError:
    google_genai = None
    genai_types = None


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(STATIC_DIR, "meme_templates")
LATEST_DIR = os.path.join(STATIC_DIR, "latest_memes")
OG_DIR = os.path.join(STATIC_DIR, "og_memes")
IMGFLIP_CACHE_DIR = os.path.join(STATIC_DIR, "imgflip_cache")
UPLOADS_DIR = os.path.join(STATIC_DIR, "uploads")

META_PATH = os.path.join(STATIC_DIR, "templates_meta.json")
IMGFLIP_META_PATH = os.path.join(STATIC_DIR, "imgflip_meta.json")
EMBEDDINGS_PATH = os.path.join(STATIC_DIR, "template_embeddings.json")

for d in (LATEST_DIR, IMGFLIP_CACHE_DIR, UPLOADS_DIR):
    os.makedirs(d, exist_ok=True)

app = Flask(__name__, static_folder="static")
CORS(app)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB upload cap

GROQ_KEY = os.getenv("GROQ_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
# Opt-in LLM reranker on the retrieval path. Adds ~400ms per request but lifts
# top-1 template accuracy from 29% -> 54% in offline eval (scripts/eval.py).
USE_RERANKER = os.getenv("USE_RERANKER", "0").lower() in ("1", "true", "yes")

groq_client = Groq(api_key=GROQ_KEY) if (Groq and GROQ_KEY) else None

# Single Gemini client used for both text fallback and image generation.
gemini_client = None
if google_genai and GEMINI_KEY:
    try:
        gemini_client = google_genai.Client(api_key=GEMINI_KEY)
    except Exception as e:
        app.logger.warning("Gemini client init failed: %s", e)

GROQ_MODEL = "llama-3.3-70b-versatile"
GEMINI_TEXT_MODEL = "gemini-2.5-flash"
GEMINI_IMAGE_MODEL = "gemini-2.5-flash-image"
GEMINI_EMBED_MODEL = "gemini-embedding-001"

FONT_CANDIDATES = ["impact.ttf", "Impacted.ttf", "unicode.impact.ttf", "arial.ttf"]
FONT_PATH = next(
    (os.path.join(BASE_DIR, f) for f in FONT_CANDIDATES
     if os.path.exists(os.path.join(BASE_DIR, f))),
    None,
)


def _load_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path: str, data: Any) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


TEMPLATES_META: dict[str, dict] = _load_json(META_PATH, {})
IMGFLIP_META: dict[str, dict] = _load_json(IMGFLIP_META_PATH, {})


# ---------------------------------------------------------------------------
# Imgflip integration
# ---------------------------------------------------------------------------

IMGFLIP_URL = "https://api.imgflip.com/get_memes"

# How we infer a meme's likely emotion bucket from its name keywords.
EMOTION_KEYWORDS: dict[str, list[str]] = {
    "preference":   ["drake", "two buttons", "change my mind", "expanding brain", "rules"],
    "dilemma":      ["two buttons", "sweating", "decision"],
    "smug":         ["smirk", "smug", "evil", "kermit", "gru"],
    "confused":     ["confused", "math lady", "huh", "fry"],
    "exasperated":  ["facepalm", "stop", "tired"],
    "disappointed": ["disappointed", "sad", "ben affleck", "side eye"],
    "victory":      ["success kid", "winning", "yes"],
    "wholesome":    ["doge", "shiba", "happy", "cheems"],
    "schadenfreude":["leonardo dicaprio laughing", "haha", "pointing"],
    "warning":      ["this is fine", "burning", "alarm"],
    "staring":      ["staring", "side eye", "kombucha"],
    "agreement":    ["that's true", "facts", "agreed"],
    "leaving":      ["walking away", "leaving"],
    "temptation":   ["distracted boyfriend", "temptation"],
}

DEFAULT_FORMATS_BY_BOX_COUNT = {1: "single", 2: "single", 3: "labels_3"}

# Imgflip IDs that need special layouts because the empty panels aren't top+bottom.
IMGFLIP_FORMAT_OVERRIDES: dict[str, str] = {
    "181913649": "drake",          # Drake Hotline Bling
    "87743020":  "two_buttons",    # Two Buttons
    "112126428": "labels_3",       # Distracted Boyfriend
    "131087935": "drake",          # Running Away Balloon (similar split)
}


def _infer_emotions(name: str) -> list[str]:
    n = name.lower()
    matched = [emo for emo, kws in EMOTION_KEYWORDS.items()
               if any(k in n for k in kws)]
    return matched or ["relatable"]


def _imgflip_meta_from_api(meme: dict) -> dict:
    """Adapt an Imgflip API record into our internal template-meta shape."""
    box_count = int(meme.get("box_count", 1))
    override = IMGFLIP_FORMAT_OVERRIDES.get(str(meme["id"]))

    if override == "drake":
        fmt = "drake"
        text_zones = [
            {"id": "top", "position": "top_right_panel", "max_chars": 60},
            {"id": "bottom", "position": "bottom_right_panel", "max_chars": 60},
        ]
    elif override == "two_buttons":
        fmt = "two_buttons"
        text_zones = [
            {"id": "button_left", "position": "button_left", "max_chars": 30},
            {"id": "button_right", "position": "button_right", "max_chars": 30},
        ]
    elif override == "labels_3":
        fmt = "labels_3"
        text_zones = [
            {"id": "boyfriend", "position": "label_boyfriend", "max_chars": 25},
            {"id": "girlfriend", "position": "label_girlfriend", "max_chars": 25},
            {"id": "other_woman", "position": "label_other_woman", "max_chars": 25},
        ]
    elif box_count == 2:
        text_zones = [
            {"id": "top", "position": "top", "max_chars": 70},
            {"id": "bottom", "position": "bottom", "max_chars": 70},
        ]
        fmt = "single"
    elif box_count >= 3:
        text_zones = [
            {"id": f"label_{i}", "position": f"label_{i}", "max_chars": 40}
            for i in range(box_count)
        ]
        fmt = "labels_n"
    else:
        text_zones = [{"id": "top", "position": "top", "max_chars": 80}]
        fmt = "single"

    return {
        "id": f"imgflip:{meme['id']}",
        "name": meme["name"],
        "format": fmt,
        "panels": 1,
        "box_count": box_count,
        "emotions": _infer_emotions(meme["name"]),
        "use_cases": [meme["name"]],
        "caption_style": (
            "Funny, witty caption matching this template's vibe. "
            f"Output {box_count} text part(s)."
        ),
        "text_zones": text_zones,
        "source": "imgflip",
        "remote_url": meme["url"],
        "width": meme.get("width"),
        "height": meme.get("height"),
    }


def refresh_imgflip(force: bool = False) -> int:
    """Fetch trending Imgflip templates and persist their metadata. Returns count."""
    global IMGFLIP_META
    if IMGFLIP_META and not force:
        return len(IMGFLIP_META)
    try:
        r = requests.get(IMGFLIP_URL, timeout=10)
        r.raise_for_status()
        memes = r.json()["data"]["memes"]
    except Exception as e:
        app.logger.warning("Imgflip fetch failed: %s", e)
        return len(IMGFLIP_META)

    new_meta = {f"imgflip:{m['id']}": _imgflip_meta_from_api(m) for m in memes}
    IMGFLIP_META = new_meta
    _save_json(IMGFLIP_META_PATH, IMGFLIP_META)
    return len(IMGFLIP_META)


def _imgflip_cache_path(template_id: str, remote_url: str) -> str:
    """Download the imgflip image once, then return its cached local path."""
    ext = os.path.splitext(remote_url)[1].lower() or ".jpg"
    if ext not in (".jpg", ".jpeg", ".png"):
        ext = ".jpg"
    safe = template_id.replace(":", "_")
    path = os.path.join(IMGFLIP_CACHE_DIR, f"{safe}{ext}")
    if not os.path.exists(path):
        r = requests.get(remote_url, timeout=15)
        r.raise_for_status()
        with open(path, "wb") as f:
            f.write(r.content)
    return path


def _all_templates() -> dict[str, dict]:
    """Merged view of local + imgflip templates."""
    return {**TEMPLATES_META, **IMGFLIP_META}


# ---------------------------------------------------------------------------
# RAG: vision/metadata embeddings for semantic template retrieval
# ---------------------------------------------------------------------------
#
# Pipeline:
#   build-time: scripts/build_embeddings.py
#       - For local templates: embed curated metadata text (name + emotions + use_cases + style).
#       - For imgflip templates: ask Gemini Vision to describe the image, embed that.
#       - Persist to static/template_embeddings.json.
#   query-time:
#       - Embed the user's topic + analysis once per request.
#       - Cosine-similarity vs the cached matrix; blend with emotion-keyword bonus.

class _EmbStore:
    """In-memory embedding store. Lazily loads on first access."""

    def __init__(self) -> None:
        self.ids: list[str] = []
        self.matrix: np.ndarray | None = None
        self.descriptions: dict[str, str] = {}
        self.loaded = False

    def load(self) -> None:
        if self.loaded:
            return
        if not os.path.exists(EMBEDDINGS_PATH):
            self.loaded = True
            return
        with open(EMBEDDINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        ids: list[str] = []
        rows: list[list[float]] = []
        for tid, rec in data.items():
            emb = rec.get("embedding")
            if not emb:
                continue
            ids.append(tid)
            rows.append(emb)
            self.descriptions[tid] = rec.get("description", "")
        if rows:
            mat = np.asarray(rows, dtype=np.float32)
            # L2-normalize once so retrieval is just a dot product.
            norms = np.linalg.norm(mat, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            self.matrix = mat / norms
            self.ids = ids
        self.loaded = True
        app.logger.info("Loaded %d template embeddings", len(self.ids))

    def is_ready(self) -> bool:
        self.load()
        return self.matrix is not None and len(self.ids) > 0


EMB_STORE = _EmbStore()


def embed_query(text: str) -> np.ndarray | None:
    """Embed a single query string and return a unit vector, or None on failure."""
    if not gemini_client:
        return None
    try:
        cfg = (
            genai_types.EmbedContentConfig(task_type="RETRIEVAL_QUERY")
            if genai_types else None
        )
        with telemetry.call("gemini", GEMINI_EMBED_MODEL, "embed_query") as t:
            resp = gemini_client.models.embed_content(
                model=GEMINI_EMBED_MODEL,
                contents=text,
                config=cfg,
            )
            t.set_response(resp)
        v = np.asarray(resp.embeddings[0].values, dtype=np.float32)
        n = float(np.linalg.norm(v))
        return v / n if n > 0 else None
    except Exception as e:
        app.logger.warning("embed_query failed: %s", e)
        return None


def rag_rank(topic: str, analysis: dict, k: int = 12) -> list[tuple[str, float]]:
    """Return top-k (template_id, similarity) by cosine to the topic embedding."""
    EMB_STORE.load()
    if not EMB_STORE.is_ready():
        return []
    # Combine topic + analysis context for a richer query embedding
    query_text = (
        f"Topic: {topic}. Tone: {analysis.get('tone', '')}. "
        f"Emotion: {analysis.get('emotion', '')}. "
        f"Context: {analysis.get('cultural_context', '')}. "
        f"Keywords: {', '.join(analysis.get('keywords', []))}."
    )
    qv = embed_query(query_text)
    if qv is None or EMB_STORE.matrix is None:
        return []
    sims = EMB_STORE.matrix @ qv  # shape (N,) since both are unit-normalized
    idx_sorted = np.argsort(-sims)[:k]
    return [(EMB_STORE.ids[i], float(sims[i])) for i in idx_sorted]


def rerank_with_llm(
    topic: str,
    analysis: dict,
    candidates: list[tuple[str, float]],
    pool: dict[str, dict] | None = None,
    top_k: int = 10,
) -> list[tuple[str, float]]:
    """LLM reranker over RAG candidates.

    Takes the retriever's top-N (template_id, sim) candidates and asks Groq
    Llama-3.3-70B to rescore them on a 0-10 scale by topic fit, using each
    template's curated metadata as context. Standard retriever -> reranker
    pattern: retriever gives recall, reranker gives precision.

    Returns the reranked list as (template_id, llm_score). On any failure
    (no Groq, bad JSON, network), returns the input candidates unchanged so
    callers can rely on a non-empty list.
    """
    if not candidates:
        return []
    pool = pool if pool is not None else _all_templates()
    # Trim down so the prompt stays under a few hundred tokens
    short = candidates[: min(20, len(candidates))]

    lines = []
    for i, (tid, sim) in enumerate(short, 1):
        meta = pool.get(tid, {})
        emos = ", ".join(meta.get("emotions", [])) or "—"
        uc = "; ".join(meta.get("use_cases", [])[:2]) or "—"
        lines.append(
            f"[{i}] {meta.get('name', tid)}  "
            f"(emotions: {emos}; use_cases: {uc}; sim: {sim:.3f})"
        )
    rendered = "\n".join(lines)

    system = (
        "You are reranking meme templates for a given topic. "
        "Pick templates whose mood/scenario fits the topic — not just keyword overlap. "
        "Return strict JSON only."
    )
    user = f"""Topic: "{topic}"
Tone: {analysis.get('tone', '')}
Emotion: {analysis.get('emotion', '')}
Cultural context: {analysis.get('cultural_context', '')}

Candidate templates (1-indexed):
{rendered}

Rate each candidate 0-10 on how well it fits THIS specific topic.
Return JSON:
{{"rankings": [{{"index": <1-based int>, "score": <0-10 float>}}]}}
Include ALL candidates. No prose, no markdown."""

    try:
        result = _groq_json(system, user, temperature=0.2, op="rerank")
    except Exception as e:
        app.logger.warning("LLM rerank failed (%s); returning retriever order.", e)
        return short

    rankings = result.get("rankings", []) if isinstance(result, dict) else []
    by_idx: dict[int, float] = {}
    for r in rankings:
        if not isinstance(r, dict):
            continue
        try:
            idx = int(r.get("index"))
            sc = float(r.get("score", 0.0))
        except (TypeError, ValueError):
            continue
        by_idx[idx] = sc

    rescored: list[tuple[str, float]] = []
    for i, (tid, sim) in enumerate(short, 1):
        # If the LLM skipped a candidate, keep it but at a low score so it falls back.
        sc = by_idx.get(i, sim * 5.0)  # rough scale match
        rescored.append((tid, sc))
    rescored.sort(key=lambda x: -x[1])
    return rescored[:top_k]


# ---------------------------------------------------------------------------
# LLM helpers
# ---------------------------------------------------------------------------

def _groq_json(system: str, user: str, *, temperature: float = 0.9,
               op: str = "groq_json") -> dict:
    """Call Groq in JSON mode with one retry that explicitly nags about valid JSON."""
    if not groq_client:
        raise RuntimeError("Groq not configured")
    hardened_system = (
        system + " IMPORTANT: respond with VALID JSON only. "
        "All string values must be wrapped in double-quotes. "
        "Escape any inner double-quotes as \\\". Do not use single-quote string syntax."
    )
    last_err: Exception | None = None
    for attempt in range(2):
        try:
            with telemetry.call("groq", GROQ_MODEL, op) as t:
                resp = groq_client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[
                        {"role": "system", "content": hardened_system},
                        {"role": "user", "content": user},
                    ],
                    response_format={"type": "json_object"},
                    temperature=temperature if attempt == 0 else 0.4,
                    max_tokens=512,
                )
                t.set_response(resp)
            content = resp.choices[0].message.content or ""
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Try to recover by unquoting smart quotes / fixing common issues
                fixed = content.replace("“", '"').replace("”", '"')
                return json.loads(fixed)
        except Exception as e:
            last_err = e
            continue
    raise last_err if last_err else RuntimeError("Groq JSON failed")


def _gemini_json(prompt: str, *, op: str = "gemini_json") -> dict:
    if not gemini_client:
        raise RuntimeError("Gemini not configured")
    with telemetry.call("gemini", GEMINI_TEXT_MODEL, op) as t:
        resp = gemini_client.models.generate_content(
            model=GEMINI_TEXT_MODEL,
            contents=prompt,
        )
        t.set_response(resp)
    text = (resp.text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)


def analyze_topic(topic: str) -> dict:
    system = (
        "You analyze a topic for meme generation. "
        "Respond with strict JSON only — no prose, no markdown."
    )
    user = f"""Analyze this topic for a meme:

Topic: "{topic}"

Return JSON with this exact shape:
{{
  "sentiment": "positive" | "negative" | "neutral" | "mixed",
  "tone": "sarcastic" | "wholesome" | "absurd" | "edgy" | "relatable" | "ironic",
  "emotion": one of: chill, confused, smug, fragile, exasperated, preference, warning, avoidance, agreement, disappointed, temptation, wholesome, curious, repetition, staring, what, serious, leaving, victory, stop_it, dilemma, welcoming, schadenfreude,
  "cultural_context": short phrase describing the cultural/social context,
  "keywords": [3-5 short keywords]
}}"""
    try:
        return _groq_json(system, user, op="analyze")
    except Exception as e:
        app.logger.warning("Groq analyze failed (%s); trying Gemini.", e)
        try:
            return _gemini_json(system + "\n\n" + user, op="analyze")
        except Exception as e2:
            app.logger.error("Both analyze providers failed: %s", e2)
            return {
                "sentiment": "neutral", "tone": "relatable",
                "emotion": "relatable", "cultural_context": topic,
                "keywords": [topic],
            }


def _emotion_bonus(meta: dict, analysis: dict) -> float:
    """Cheap rule-based bonus on top of the cosine similarity."""
    target_emotion = (analysis.get("emotion") or "").lower()
    keywords = [k.lower() for k in analysis.get("keywords", [])]
    bonus = 0.0
    emotions = [e.lower() for e in meta.get("emotions", [])]
    if target_emotion and target_emotion in emotions:
        bonus += 0.20
    for e in emotions:
        if any(k in e or e in k for k in keywords):
            bonus += 0.04
    for uc in meta.get("use_cases", []):
        if any(k in uc.lower() for k in keywords):
            bonus += 0.06
    return min(bonus, 0.4)  # cap so it can't dominate cosine signal


def pick_template(
    analysis: dict,
    exclude: set[str] | None = None,
    pool: dict[str, dict] | None = None,
    *,
    topic: str | None = None,
) -> tuple[str, dict]:
    """
    Hybrid retrieval: cosine similarity (semantic RAG) + emotion match bonus.
    Falls back to keyword scoring if embeddings aren't loaded or query embed fails.
    """
    exclude = exclude or set()
    pool = pool if pool is not None else _all_templates()

    rag_hits: list[tuple[str, float]] = []
    if topic and EMB_STORE.is_ready():
        rag_hits = rag_rank(topic, analysis, k=20)

    if rag_hits:
        # Filter against exclude / availability before any rescoring.
        available = [
            (tid, sim) for tid, sim in rag_hits
            if tid not in exclude and tid in pool
            and _template_image_available(tid, pool[tid])
        ]
        if USE_RERANKER and topic and len(available) > 1:
            # Retriever -> reranker: ask LLM to rescore top candidates by topic fit.
            available = rerank_with_llm(topic, analysis, available, pool=pool, top_k=10)

        scored: list[tuple[float, str]] = []
        for tid, sim in available:
            meta = pool[tid]
            # When reranker ran, `sim` is already an LLM 0-10 score; emotion bonus
            # (which is in cosine units, ~0-0.4) becomes negligible — keep it for
            # consistency / tie-breaking but it won't dominate.
            score = sim + _emotion_bonus(meta, analysis)
            score += random.uniform(0, 0.02)  # tiny jitter to avoid ties on repeat
            scored.append((score, tid))
        if scored:
            scored.sort(reverse=True)
            top = scored[: min(5, len(scored))]
            weights = [max(0.01, s) for s, _ in top]
            chosen = random.choices(top, weights=weights, k=1)[0][1]
            return chosen, pool[chosen]

    # Fallback: original keyword-based scoring (used when no embeddings or embed fails)
    target_emotion = (analysis.get("emotion") or "").lower()
    keywords = [k.lower() for k in analysis.get("keywords", [])]
    context = (analysis.get("cultural_context") or "").lower()
    fallback_scored: list[tuple[int, str]] = []
    for tid, meta in pool.items():
        if tid in exclude or not _template_image_available(tid, meta):
            continue
        score = 0
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
            if context and any(w in uc_l for w in context.split() if len(w) > 3):
                score += 1
        if meta.get("source") != "imgflip":
            score += 1
        score += random.randint(0, 2)
        fallback_scored.append((score, tid))

    if not fallback_scored:
        raise RuntimeError("No templates available")
    fallback_scored.sort(reverse=True)
    top = fallback_scored[: min(5, len(fallback_scored))]
    weights = [max(1, s) for s, _ in top]
    chosen = random.choices(top, weights=weights, k=1)[0][1]
    return chosen, pool[chosen]


def _template_image_available(tid: str, meta: dict) -> bool:
    if meta.get("source") == "imgflip":
        return bool(meta.get("remote_url"))
    return os.path.exists(os.path.join(TEMPLATES_DIR, tid))


def template_image_path(tid: str, meta: dict) -> str:
    if meta.get("source") == "imgflip":
        return _imgflip_cache_path(tid, meta["remote_url"])
    return os.path.join(TEMPLATES_DIR, tid)


def write_caption(topic: str, analysis: dict, template_meta: dict) -> dict:
    zones = template_meta.get("text_zones", [])
    zone_ids = [z["id"] for z in zones]
    zones_desc = "\n".join(
        f'- "{z["id"]}" (max ~{z["max_chars"]} chars)' for z in zones
    )
    system = (
        "You write meme captions. Be funny, witty, culturally aware, and concise. "
        "Match the meme template's style. Return strict JSON only."
    )
    example = "{" + ", ".join(f'"{zid}": "..."' for zid in zone_ids) + "}"
    user = f"""Write a meme caption for this template.

Topic: "{topic}"
Topic analysis: {json.dumps(analysis)}

Template: {template_meta.get('name')}
Style guide: {template_meta.get('caption_style')}

The JSON object you return MUST have EXACTLY these keys (no other keys):
{zones_desc}

Example shape: {example}

Each value should be plain text. Keep within character hints. No markdown, no extra keys."""

    try:
        result = _groq_json(system, user, op="write_caption")
    except Exception as e:
        app.logger.warning("Groq caption failed (%s); trying Gemini.", e)
        try:
            result = _gemini_json(system + "\n\n" + user, op="write_caption")
        except Exception:
            result = {z["id"]: topic for z in zones}

    # Backfill any missing zone with the next non-empty value (handles LLM key drift)
    extras = [v for k, v in result.items() if k not in zone_ids and v]
    for z in zones:
        if not result.get(z["id"]) and extras:
            result[z["id"]] = extras.pop(0)
        result.setdefault(z["id"], "")
    return result


def write_captions_n(topic: str, analysis: dict, template_meta: dict,
                     n: int = 5) -> list[dict]:
    """Generate N caption candidates in a single LLM call (parallel ideation)."""
    zones = template_meta.get("text_zones", [])
    zone_ids = [z["id"] for z in zones]
    zones_desc = "\n".join(
        f'- "{z["id"]}" (max ~{z["max_chars"]} chars)' for z in zones
    )
    example_obj = "{" + ", ".join(f'"{zid}": "..."' for zid in zone_ids) + "}"
    system = (
        "You write meme captions. Brainstorm DIVERSE candidates — each should take "
        "a different angle (literal, ironic, absurd, self-deprecating, etc.). "
        "Return strict JSON only."
    )
    user = f"""Generate {n} DIFFERENT caption candidates for this meme template.

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

    try:
        result = _groq_json(system, user, op="write_captions_n")
        cands = result.get("candidates", [])
    except Exception as e:
        app.logger.warning("Groq write_captions_n failed (%s); trying Gemini.", e)
        try:
            result = _gemini_json(system + "\n\n" + user, op="write_captions_n")
            cands = result.get("candidates", [])
        except Exception:
            cands = []

    # Backfill missing zone keys per candidate
    cleaned: list[dict] = []
    for c in cands:
        if not isinstance(c, dict):
            continue
        # Backfill zone keys from any extra keys (LLM key-drift recovery)
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
    if not cleaned:
        # Fallback to single-call write_caption
        cleaned = [write_caption(topic, analysis, template_meta)]
    return cleaned


def judge_captions(topic: str, template_meta: dict,
                   candidates: list[dict]) -> list[dict]:
    """Have an LLM rank caption candidates by humor / relevance / fit. Returns
    [{captions, score, reason}] sorted desc by score."""
    if len(candidates) <= 1:
        return [{"captions": candidates[0] if candidates else {}, "score": 10.0,
                 "reason": "Only candidate."}]

    rendered = "\n".join(
        f"  [{i + 1}] " + json.dumps(c, ensure_ascii=False)
        for i, c in enumerate(candidates)
    )
    system = (
        "You are an expert meme critic. Judge meme caption candidates for a "
        "specific template. Return strict JSON only."
    )
    user = f"""Rate these {len(candidates)} caption candidates for the meme template.

Topic: "{topic}"
Template: {template_meta.get('name')}
Style guide: {template_meta.get('caption_style')}

Candidates (1-indexed):
{rendered}

Score each on a 0-10 scale across: humor, topic_relevance, template_fit.
Compute "overall" as (humor*0.5 + topic_relevance*0.25 + template_fit*0.25).
Return JSON:
{{
  "rankings": [
    {{"index": <1-based>, "humor": <0-10>, "topic_relevance": <0-10>, "template_fit": <0-10>, "overall": <0-10>, "reason": "<one short sentence>"}}
  ]
}}
List ALL candidates in your rankings array. No markdown."""

    try:
        result = _groq_json(system, user, temperature=0.3, op="judge_captions")
    except Exception as e:
        app.logger.warning("Groq judge failed (%s); trying Gemini.", e)
        try:
            result = _gemini_json(system + "\n\n" + user, op="judge_captions")
        except Exception:
            # Degenerate: just return the first candidate as winner
            return [{"captions": c, "score": 0.0, "reason": "judge unavailable"}
                    for c in candidates]

    rankings = result.get("rankings", [])
    by_idx = {r.get("index"): r for r in rankings if isinstance(r, dict)}
    out: list[dict] = []
    for i, c in enumerate(candidates):
        r = by_idx.get(i + 1) or {}
        score = float(r.get("overall", 0.0) or 0.0)
        reason = r.get("reason", "")
        out.append({
            "captions": c,
            "score": round(score, 2),
            "humor": float(r.get("humor", 0.0) or 0.0),
            "relevance": float(r.get("topic_relevance", 0.0) or 0.0),
            "fit": float(r.get("template_fit", 0.0) or 0.0),
            "reason": reason,
        })
    out.sort(key=lambda x: x["score"], reverse=True)
    return out


def write_caption_for_image(topic: str, analysis: dict,
                            image_path: str | None = None,
                            zones: list[dict] | None = None) -> dict:
    """Generic caption writer for upload / fresh modes (no template_meta available)."""
    zones = zones or [
        {"id": "top", "position": "top", "max_chars": 70},
        {"id": "bottom", "position": "bottom", "max_chars": 70},
    ]
    fake_meta = {
        "name": "Custom image",
        "caption_style": "Top + bottom Impact-style meme caption. Punchline on bottom.",
        "text_zones": zones,
    }
    return write_caption(topic, analysis, fake_meta)


# ---------------------------------------------------------------------------
# Image rendering
# ---------------------------------------------------------------------------

def _font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_PATH, size) if FONT_PATH else ImageFont.load_default()


def _wrap_to_fit(draw: ImageDraw.ImageDraw, text: str,
                 font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        candidate = (cur + " " + w).strip()
        if draw.textlength(candidate, font=font) <= max_width:
            cur = candidate
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


def _fit_text(draw: ImageDraw.ImageDraw, text: str, max_width: int,
              max_height: int, start_size: int, min_size: int = 14
              ) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    text = (text or "").upper().strip()
    size = start_size
    while size >= min_size:
        font = _font(size)
        lines = _wrap_to_fit(draw, text, font, max_width)
        line_h = font.getbbox("Ag")[3] - font.getbbox("Ag")[1]
        total_h = line_h * len(lines) + (len(lines) - 1) * 4
        if total_h <= max_height:
            return font, lines
        size -= 2
    font = _font(min_size)
    return font, _wrap_to_fit(draw, text, font, max_width)


def _draw_centered(draw: ImageDraw.ImageDraw, lines: list[str],
                   font: ImageFont.FreeTypeFont, x_center: int, y_top: int,
                   fill: str = "white", stroke: str = "black",
                   stroke_width: int | None = None) -> None:
    if stroke_width is None:
        stroke_width = max(2, font.size // 15)
    line_h = font.getbbox("Ag")[3] - font.getbbox("Ag")[1]
    y = y_top
    for line in lines:
        w = draw.textlength(line, font=font)
        draw.text((x_center - w / 2, y), line, font=font,
                  fill=fill, stroke_width=stroke_width, stroke_fill=stroke)
        y += line_h + 4


def render_classic(template_path: str, top: str, bottom: str) -> Image.Image:
    img = Image.open(template_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    W, H = img.size
    pad = int(W * 0.04)
    text_w = W - 2 * pad
    zone_h = int(H * 0.22)
    start_size = max(28, int(W / 12))
    if top:
        font, lines = _fit_text(draw, top, text_w, zone_h, start_size)
        _draw_centered(draw, lines, font, W // 2, pad)
    if bottom:
        font, lines = _fit_text(draw, bottom, text_w, zone_h, start_size)
        line_h = font.getbbox("Ag")[3] - font.getbbox("Ag")[1]
        total_h = line_h * len(lines) + (len(lines) - 1) * 4
        _draw_centered(draw, lines, font, W // 2, H - pad - total_h)
    return img


def render_drake(template_path: str, top: str, bottom: str) -> Image.Image:
    img = Image.open(template_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    W, H = img.size
    right_x = W // 2
    panel_w = W - right_x
    pad = int(panel_w * 0.08)
    text_w = panel_w - 2 * pad
    panel_h = H // 2
    text_h = panel_h - 2 * pad
    start_size = max(22, int(panel_w / 14))
    for text, panel_top in ((top, 0), (bottom, panel_h)):
        if not text:
            continue
        font, lines = _fit_text(draw, text, text_w, text_h, start_size)
        line_h = font.getbbox("Ag")[3] - font.getbbox("Ag")[1]
        total_h = line_h * len(lines) + (len(lines) - 1) * 4
        y = panel_top + (panel_h - total_h) // 2
        _draw_centered(draw, lines, font, right_x + panel_w // 2, y,
                       fill="black", stroke="white", stroke_width=2)
    return img


def render_two_buttons(template_path: str, left: str, right: str) -> Image.Image:
    img = Image.open(template_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    W, H = img.size
    btn_w = int(W * 0.36)
    btn_h = int(H * 0.18)
    btn_y_center = int(H * 0.30)
    start_size = max(18, int(W / 22))
    for label, cx in [(left, int(W * 0.27)), (right, int(W * 0.62))]:
        if not label:
            continue
        font, lines = _fit_text(draw, label, btn_w, btn_h, start_size)
        line_h = font.getbbox("Ag")[3] - font.getbbox("Ag")[1]
        total_h = line_h * len(lines) + (len(lines) - 1) * 4
        _draw_centered(draw, lines, font, cx, btn_y_center - total_h // 2,
                       fill="black", stroke="white", stroke_width=2)
    return img


def render_distracted_boyfriend(template_path: str, boyfriend: str,
                                girlfriend: str, other_woman: str) -> Image.Image:
    img = Image.open(template_path).convert("RGB")
    W, H = img.size
    strip = int(H * 0.12)
    canvas = Image.new("RGB", (W, H + strip), "white")
    canvas.paste(img, (0, strip))
    draw = ImageDraw.Draw(canvas)
    label_w = int(W / 3.2)
    start_size = max(16, int(W / 28))
    for label, cx in [(other_woman, int(W * 0.18)),
                      (boyfriend, int(W * 0.50)),
                      (girlfriend, int(W * 0.82))]:
        if not label:
            continue
        font, lines = _fit_text(draw, label, label_w, strip - 8, start_size)
        _draw_centered(draw, lines, font, cx, 4)
    return canvas


def render_labels_n(template_path: str, captions: dict) -> Image.Image:
    """Generic n-label render: stack labels above the image."""
    img = Image.open(template_path).convert("RGB")
    W, H = img.size
    items = [v for k, v in captions.items() if v]
    n = max(1, len(items))
    strip = int(H * 0.15)
    canvas = Image.new("RGB", (W, H + strip), "white")
    canvas.paste(img, (0, strip))
    draw = ImageDraw.Draw(canvas)
    cell_w = W // n
    start_size = max(16, int(W / (n * 12)))
    for i, label in enumerate(items):
        cx = cell_w * i + cell_w // 2
        font, lines = _fit_text(draw, label, cell_w - 12, strip - 8, start_size)
        _draw_centered(draw, lines, font, cx, 4)
    return canvas


def render_meme(template_path: str, meta: dict, captions: dict) -> Image.Image:
    fmt = meta.get("format", "single")
    if fmt == "drake":
        return render_drake(template_path, captions.get("top", ""), captions.get("bottom", ""))
    if fmt == "two_buttons":
        return render_two_buttons(
            template_path,
            captions.get("button_left", ""),
            captions.get("button_right", ""),
        )
    if fmt == "labels_3":
        return render_distracted_boyfriend(
            template_path,
            captions.get("boyfriend", ""),
            captions.get("girlfriend", ""),
            captions.get("other_woman", ""),
        )
    if fmt == "labels_n":
        return render_labels_n(template_path, captions)
    return render_classic(template_path,
                          captions.get("top", ""),
                          captions.get("bottom", ""))


# ---------------------------------------------------------------------------
# Fresh mode — Gemini Nano Banana
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Comic mode — narrative arc across multiple panels
# ---------------------------------------------------------------------------

def write_comic_arc(topic: str, analysis: dict, n_panels: int = 3) -> list[dict]:
    """Ask the LLM for an N-panel narrative beat sheet.
    Returns [{title, beat, emotion, caption}]."""
    if n_panels == 2:
        beats_desc = "Two-panel: setup -> punchline."
    else:
        beats_desc = "Three-panel: setup -> escalation/twist -> punchline."
    valid_emotions = (
        "chill, confused, smug, fragile, exasperated, preference, warning, "
        "avoidance, agreement, disappointed, temptation, wholesome, curious, "
        "repetition, staring, what, serious, leaving, victory, stop_it, "
        "dilemma, welcoming, schadenfreude"
    )
    system = (
        "You write SHORT meme-comic narratives that escalate to a punchline. "
        "Return strict JSON only."
    )
    user = f"""Write a {n_panels}-panel meme comic narrative.

Topic: "{topic}"
Topic analysis: {json.dumps(analysis)}

Format ({beats_desc}). Each panel should reuse the topic but progress narratively.

For each panel return:
- "title": one or two words for the beat (e.g. "Setup", "Reality", "Punchline")
- "beat": one sentence describing what happens in this panel
- "emotion": one of [{valid_emotions}] best matching this beat
- "caption": short, punchy meme text for this panel (under 80 chars)

Return JSON: {{"panels": [<obj>, <obj>, ...]}} with exactly {n_panels} items."""

    try:
        result = _groq_json(system, user, temperature=1.0, op="comic_arc")
    except Exception as e:
        app.logger.warning("Groq comic arc failed (%s); trying Gemini.", e)
        try:
            result = _gemini_json(system + "\n\n" + user)
        except Exception:
            result = {"panels": []}
    panels = result.get("panels", [])
    # Normalize / clamp to requested count
    panels = [p for p in panels if isinstance(p, dict)][:n_panels]
    while len(panels) < n_panels:
        panels.append({"title": f"Panel {len(panels)+1}", "beat": topic,
                       "emotion": analysis.get("emotion", "relatable"),
                       "caption": topic})
    return panels


def render_comic(panel_results: list[dict]) -> Image.Image:
    """Stack rendered panels vertically with thin gutters and panel labels."""
    if not panel_results:
        raise RuntimeError("no panels")
    # Normalize all panels to same width = max(panel widths)
    target_w = max(p["image"].width for p in panel_results)
    rendered_panels: list[Image.Image] = []
    for p in panel_results:
        img = p["image"]
        if img.width != target_w:
            ratio = target_w / img.width
            img = img.resize((target_w, int(img.height * ratio)), Image.LANCZOS)
        rendered_panels.append(img)

    label_h = max(36, target_w // 22)
    gutter = max(6, target_w // 100)
    total_h = sum(im.height for im in rendered_panels) + label_h * len(rendered_panels) + gutter * (len(rendered_panels) - 1)
    canvas = Image.new("RGB", (target_w, total_h), "white")
    draw = ImageDraw.Draw(canvas)

    y = 0
    for i, (p, img) in enumerate(zip(panel_results, rendered_panels)):
        # Panel header strip
        draw.rectangle([0, y, target_w, y + label_h], fill=(20, 20, 20))
        title = f"PANEL {i + 1} · {p.get('title', '').upper()}"
        font = _font(max(14, label_h // 2))
        tw = draw.textlength(title, font=font)
        draw.text(((target_w - tw) / 2,
                   y + (label_h - (font.getbbox('Ag')[3] - font.getbbox('Ag')[1])) / 2 - 2),
                  title, font=font, fill="white")
        y += label_h
        canvas.paste(img, (0, y))
        y += img.height
        if i < len(rendered_panels) - 1:
            y += gutter

    return canvas


class FreshImageError(RuntimeError):
    """Carries a user-friendly reason for why image generation failed."""


def generate_fresh_image(topic: str, analysis: dict) -> Image.Image:
    """Ask Gemini 2.5 Flash Image for an original meme background. Raises FreshImageError on failure."""
    if not gemini_client:
        raise FreshImageError("Gemini API key not configured")
    prompt = (
        f"A square meme background image about: {topic}. "
        f"Style: bold, expressive, illustrated meme art. "
        f"Tone: {analysis.get('tone', 'relatable')}. "
        f"Emotion: {analysis.get('emotion', 'funny')}. "
        f"Leave clear empty space at the top and bottom for white text overlay. "
        f"No text in the image. High contrast. Clean composition."
    )
    try:
        config = (
            genai_types.GenerateContentConfig(response_modalities=["IMAGE"])
            if genai_types else None
        )
        with telemetry.call("gemini", GEMINI_IMAGE_MODEL, "fresh_image") as t:
            resp = gemini_client.models.generate_content(
                model=GEMINI_IMAGE_MODEL,
                contents=prompt,
                config=config,
            )
            t.set_response(resp)
        for part in resp.candidates[0].content.parts:
            inline = getattr(part, "inline_data", None)
            if inline and getattr(inline, "data", None):
                data = inline.data
                if isinstance(data, str):
                    import base64
                    data = base64.b64decode(data)
                return Image.open(io.BytesIO(data)).convert("RGB")
        raise FreshImageError("Gemini returned no image. Try Smart mode.")
    except FreshImageError:
        raise
    except Exception as e:
        msg = str(e)
        app.logger.warning("Gemini image gen failed: %s", msg)
        if "RESOURCE_EXHAUSTED" in msg or "429" in msg:
            raise FreshImageError(
                "Fresh mode needs a paid-tier Gemini key — image generation isn't "
                "in the free tier. Enable billing in Google AI Studio, or use Smart mode."
            )
        if "PERMISSION_DENIED" in msg or "403" in msg:
            raise FreshImageError("Your Gemini key isn't allowed to call image models.")
        raise FreshImageError(f"Gemini image generation failed: {msg[:140]}")


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def save_meme(img: Image.Image) -> str:
    fname = f"meme_{int(time.time())}_{uuid.uuid4().hex[:8]}.jpg"
    path = os.path.join(LATEST_DIR, fname)
    img.save(path, "JPEG", quality=88, optimize=True)
    return f"/static/latest_memes/{fname}"


def cleanup_latest(keep: int = 60) -> None:
    try:
        files = [f for f in os.listdir(LATEST_DIR)
                 if f.lower().endswith((".jpg", ".jpeg", ".png"))]
        files.sort(key=lambda n: os.path.getmtime(os.path.join(LATEST_DIR, n)),
                   reverse=True)
        for stale in files[keep:]:
            try:
                os.remove(os.path.join(LATEST_DIR, stale))
            except OSError:
                pass
    except FileNotFoundError:
        pass


# ---------------------------------------------------------------------------
# Trending topics — curated list refreshed per session start
# ---------------------------------------------------------------------------

TRENDING_TOPICS = [
    "Monday morning meetings",
    "AI replacing my job",
    "Indian parents and marks",
    "Trying to wake up early",
    "Code that works only on my machine",
    "When the WiFi disconnects mid-call",
    "Trying to save money at month start",
    "Gym vs Netflix",
    "ChatGPT down for 5 minutes",
    "Indian wedding food queue",
    "When mom asks where you are",
    "Submitting assignment 1 minute before deadline",
    "Friday vs Monday energy",
    "Adulting after college",
    "Tech interview rounds",
    "When the boss says 'quick call'",
]


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@app.get("/")
def home():
    return jsonify({
        "service": "MemeMind",
        "status": "ok",
        "providers": {
            "groq": bool(groq_client),
            "gemini": bool(gemini_client),
        },
        "templates": {
            "local": len(TEMPLATES_META),
            "imgflip_cached": len(IMGFLIP_META),
        },
        "rag": {
            "enabled": EMB_STORE.is_ready(),
            "indexed": len(EMB_STORE.ids),
        },
    })


@app.post("/api/analyze")
def api_analyze():
    data = request.get_json(silent=True) or {}
    topic = (data.get("topic") or "").strip()
    if not topic:
        abort(400, "topic required")
    return jsonify(analyze_topic(topic))


@app.post("/api/generate")
def api_generate():
    """Smart mode generate. Body: {topic, template_id?}"""
    data = request.get_json(silent=True) or {}
    topic = (data.get("topic") or "").strip()
    if not topic:
        return jsonify({"error": "topic required"}), 400

    explicit = data.get("template_id")
    pool = _all_templates()
    analysis = analyze_topic(topic)

    if explicit and explicit in pool:
        tid = explicit
        meta = pool[tid]
        retrieval = "explicit"
    else:
        tid, meta = pick_template(analysis, pool=pool, topic=topic)
        retrieval = "rag" if EMB_STORE.is_ready() else "keyword"

    use_judge = bool(data.get("judge", True))
    judge_data: dict | None = None
    if use_judge:
        candidates = write_captions_n(topic, analysis, meta, n=5)
        ranked = judge_captions(topic, meta, candidates)
        captions = ranked[0]["captions"] if ranked else write_caption(topic, analysis, meta)
        judge_data = {
            "winner_score": ranked[0]["score"] if ranked else None,
            "winner_reason": ranked[0].get("reason", "") if ranked else "",
            "candidates_total": len(candidates),
            "all": ranked,
        }
    else:
        captions = write_caption(topic, analysis, meta)

    img = render_meme(template_image_path(tid, meta), meta, captions)
    url = save_meme(img)

    threading.Thread(target=cleanup_latest, daemon=True).start()
    return jsonify({
        "mode": "smart",
        "url": url,
        "topic": topic,
        "template": {"id": tid, "name": meta.get("name"),
                     "format": meta.get("format"),
                     "source": meta.get("source", "local")},
        "captions": captions,
        "analysis": analysis,
        "retrieval": retrieval,
        "judge": judge_data,
    })


@app.post("/api/generate_variants")
def api_generate_variants():
    data = request.get_json(silent=True) or {}
    topic = (data.get("topic") or "").strip()
    if not topic:
        return jsonify({"error": "topic required"}), 400
    n = max(1, min(int(data.get("n", 3)), 4))

    analysis = analyze_topic(topic)
    pool = _all_templates()
    used: set[str] = set()
    variants: list[dict] = []

    for _ in range(n):
        try:
            tid, meta = pick_template(analysis, exclude=used, pool=pool, topic=topic)
        except RuntimeError:
            break
        used.add(tid)
        try:
            captions = write_caption(topic, analysis, meta)
            img = render_meme(template_image_path(tid, meta), meta, captions)
            url = save_meme(img)
            variants.append({
                "url": url,
                "template": {"id": tid, "name": meta.get("name"),
                             "format": meta.get("format"),
                             "source": meta.get("source", "local")},
                "captions": captions,
            })
        except Exception as e:
            app.logger.exception("Variant render failed: %s", e)
            continue

    threading.Thread(target=cleanup_latest, daemon=True).start()
    return jsonify({
        "mode": "smart",
        "topic": topic,
        "analysis": analysis,
        "variants": variants,
        "retrieval": "rag" if EMB_STORE.is_ready() else "keyword",
    })


@app.post("/api/generate_fresh")
def api_generate_fresh():
    """Fresh mode — Gemini Nano Banana generates the image, we add the caption."""
    data = request.get_json(silent=True) or {}
    topic = (data.get("topic") or "").strip()
    if not topic:
        return jsonify({"error": "topic required"}), 400
    if not gemini_client:
        return jsonify({
            "error": "Fresh mode requires GEMINI_API_KEY with image-generation access."
        }), 503

    analysis = analyze_topic(topic)
    try:
        bg = generate_fresh_image(topic, analysis)
    except FreshImageError as e:
        return jsonify({"error": str(e), "fallback": "smart"}), 502

    captions = write_caption_for_image(topic, analysis)
    # Save bg to temp path so render_classic can reuse the same code path
    tmp_path = os.path.join(IMGFLIP_CACHE_DIR, f"_fresh_{uuid.uuid4().hex}.jpg")
    bg.save(tmp_path, "JPEG", quality=92)
    try:
        img = render_classic(tmp_path, captions.get("top", ""), captions.get("bottom", ""))
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
    url = save_meme(img)
    threading.Thread(target=cleanup_latest, daemon=True).start()
    return jsonify({
        "mode": "fresh",
        "url": url,
        "topic": topic,
        "captions": captions,
        "analysis": analysis,
    })


@app.post("/api/generate_comic")
def api_generate_comic():
    """Comic mode — multi-panel narrative meme."""
    data = request.get_json(silent=True) or {}
    topic = (data.get("topic") or "").strip()
    if not topic:
        return jsonify({"error": "topic required"}), 400
    n_panels = max(2, min(int(data.get("panels", 3)), 4))

    analysis = analyze_topic(topic)
    pool = _all_templates()
    arc = write_comic_arc(topic, analysis, n_panels=n_panels)

    # For comic panels, restrict to clean single/drake/two_buttons formats — labels_n
    # templates are usually multi-image collages and look bad inside a comic frame.
    panel_pool = {
        tid: meta for tid, meta in pool.items()
        if meta.get("format") in ("single", "drake", "two_buttons")
    }

    used: set[str] = set()
    panel_results: list[dict] = []
    for beat in arc:
        beat_analysis = {
            **analysis,
            "emotion": beat.get("emotion", analysis.get("emotion", "relatable")),
        }
        try:
            tid, meta = pick_template(beat_analysis, exclude=used,
                                       pool=panel_pool,
                                       topic=f"{topic} {beat.get('beat', '')}")
        except RuntimeError:
            continue
        used.add(tid)

        # Comic panel captions: prefer the LLM-authored beat caption verbatim.
        zones = meta.get("text_zones", [])
        beat_caption = (beat.get("caption") or "").strip()
        if len(zones) == 1:
            captions = {zones[0]["id"]: beat_caption or beat.get("beat", "")}
        elif len(zones) == 2 and beat_caption:
            # Split the beat caption into two halves at the nearest space past midpoint
            mid = len(beat_caption) // 2
            split_at = beat_caption.find(" ", mid)
            if split_at == -1:
                split_at = mid
            captions = {
                zones[0]["id"]: beat_caption[:split_at].strip(),
                zones[1]["id"]: beat_caption[split_at:].strip() or beat.get("beat", ""),
            }
        else:
            # Fall back to a fresh LLM caption rooted in this beat
            captions = write_caption(beat.get("beat") or topic, beat_analysis, meta)

        try:
            img = render_meme(template_image_path(tid, meta), meta, captions)
        except Exception as e:
            app.logger.warning("Panel render failed: %s", e)
            continue
        panel_results.append({
            "image": img,
            "title": beat.get("title", ""),
            "beat": beat.get("beat", ""),
            "emotion": beat.get("emotion", ""),
            "caption": beat.get("caption", ""),
            "template": {"id": tid, "name": meta.get("name"),
                         "format": meta.get("format"),
                         "source": meta.get("source", "local")},
            "captions": captions,
        })

    if not panel_results:
        return jsonify({"error": "Failed to render any panel"}), 500

    comic_img = render_comic(panel_results)
    url = save_meme(comic_img)
    threading.Thread(target=cleanup_latest, daemon=True).start()

    # Strip PIL images from response
    panels_out = [{k: v for k, v in p.items() if k != "image"} for p in panel_results]
    return jsonify({
        "mode": "comic",
        "url": url,
        "topic": topic,
        "analysis": analysis,
        "panels": panels_out,
    })


@app.post("/api/caption_upload")
def api_caption_upload():
    """Upload mode — user provides image, we caption it. multipart/form-data: topic + file."""
    topic = (request.form.get("topic") or "").strip()
    if not topic:
        return jsonify({"error": "topic required"}), 400
    f = request.files.get("image")
    if not f or not f.filename:
        return jsonify({"error": "image file required"}), 400

    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        return jsonify({"error": "image must be jpg/png/webp"}), 400
    upload_path = os.path.join(UPLOADS_DIR, f"u_{uuid.uuid4().hex}{ext}")
    f.save(upload_path)

    analysis = analyze_topic(topic)
    captions = write_caption_for_image(topic, analysis)
    try:
        img = render_classic(upload_path, captions.get("top", ""), captions.get("bottom", ""))
    finally:
        try:
            os.remove(upload_path)
        except OSError:
            pass
    url = save_meme(img)
    threading.Thread(target=cleanup_latest, daemon=True).start()
    return jsonify({
        "mode": "upload",
        "url": url,
        "topic": topic,
        "captions": captions,
        "analysis": analysis,
    })


@app.post("/api/regenerate")
def api_regenerate():
    data = request.get_json(silent=True) or {}
    topic = (data.get("topic") or "").strip()
    template_id = data.get("template_id")
    pool = _all_templates()
    if not topic or not template_id or template_id not in pool:
        return jsonify({"error": "topic and valid template_id required"}), 400

    analysis = analyze_topic(topic)
    meta = pool[template_id]
    captions = write_caption(topic, analysis, meta)
    img = render_meme(template_image_path(template_id, meta), meta, captions)
    url = save_meme(img)
    return jsonify({
        "mode": "smart",
        "topic": topic,
        "url": url,
        "template": {"id": template_id, "name": meta.get("name"),
                     "format": meta.get("format"),
                     "source": meta.get("source", "local")},
        "captions": captions,
        "analysis": analysis,
    })


@app.get("/api/templates")
def api_templates():
    """Local + imgflip templates."""
    out = []
    for tid, meta in _all_templates().items():
        if not _template_image_available(tid, meta):
            continue
        if meta.get("source") == "imgflip":
            preview_url = meta["remote_url"]
        else:
            preview_url = f"/static/meme_templates/{tid}"
        out.append({
            "id": tid,
            "name": meta.get("name", tid),
            "format": meta.get("format", "single"),
            "emotions": meta.get("emotions", []),
            "use_cases": meta.get("use_cases", []),
            "source": meta.get("source", "local"),
            "url": preview_url,
        })
    out.sort(key=lambda t: (t["source"] != "local", t["name"]))
    return jsonify(out)


@app.post("/api/refresh_imgflip")
def api_refresh_imgflip():
    count = refresh_imgflip(force=True)
    return jsonify({"imgflip_count": count})


@app.get("/api/og_templates")
def api_og_templates():
    if not os.path.isdir(OG_DIR):
        return jsonify([])
    files = [f for f in os.listdir(OG_DIR)
             if f.lower().endswith((".jpg", ".jpeg", ".png"))]
    files.sort()
    return jsonify([{
        "id": f,
        "name": os.path.splitext(f)[0].replace("_", " ").title(),
        "url": f"/static/og_memes/{f}",
    } for f in files])


@app.get("/api/latest")
def api_latest():
    limit = int(request.args.get("limit", 30))
    if not os.path.isdir(LATEST_DIR):
        return jsonify([])
    files = [f for f in os.listdir(LATEST_DIR)
             if f.lower().endswith((".jpg", ".jpeg", ".png"))]
    files.sort(key=lambda n: os.path.getmtime(os.path.join(LATEST_DIR, n)),
               reverse=True)
    return jsonify([{
        "url": f"/static/latest_memes/{f}",
        "created_at": int(os.path.getmtime(os.path.join(LATEST_DIR, f))),
    } for f in files[:limit]])


@app.get("/api/trending")
def api_trending():
    return jsonify(random.sample(TRENDING_TOPICS, k=min(8, len(TRENDING_TOPICS))))


# Legacy compatibility ------------------------------------------------------

@app.post("/generate_meme")
def legacy_generate():
    data = request.get_json(silent=True) or {}
    topic = (data.get("topic") or "").strip()
    if not topic:
        return jsonify({"error": "Topic not provided"}), 400
    analysis = analyze_topic(topic)
    pool = _all_templates()
    tid, meta = pick_template(analysis, pool=pool, topic=topic)
    captions = write_caption(topic, analysis, meta)
    img = render_meme(template_image_path(tid, meta), meta, captions)
    save_meme(img)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    buf.seek(0)
    return send_file(buf, mimetype="image/jpeg")


@app.get("/get_latest_memes")
def legacy_latest():
    if not os.path.isdir(LATEST_DIR):
        return jsonify([])
    files = [f for f in os.listdir(LATEST_DIR)
             if f.lower().endswith((".jpg", ".jpeg", ".png"))]
    files.sort(key=lambda n: os.path.getmtime(os.path.join(LATEST_DIR, n)),
               reverse=True)
    return jsonify([url_for("static", filename=f"latest_memes/{f}", _external=False)
                    for f in files[:15]])


@app.get("/get_og_memes")
def legacy_og():
    if not os.path.isdir(OG_DIR):
        return jsonify([])
    files = [f for f in os.listdir(OG_DIR)
             if f.lower().endswith((".jpg", ".jpeg", ".png"))]
    return jsonify([url_for("static", filename=f"og_memes/{f}", _external=False)
                    for f in files])


@app.get("/favicon.ico")
def favicon():
    return "", 204


# Pre-warm Imgflip cache on import (best-effort, non-blocking) ---------------
threading.Thread(target=lambda: refresh_imgflip(force=False), daemon=True).start()


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host="127.0.0.1", port=5000, debug=debug)
