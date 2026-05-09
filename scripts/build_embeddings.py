"""
One-shot script: build static/template_embeddings.json.

For each template (local + imgflip):
    1. Build a "description text" — for local templates we use the curated metadata
       (name + emotions + use_cases + caption_style). For imgflip templates that have
       no curated metadata, we ask Gemini Vision to describe the image.
    2. Embed that description with text-embedding-004.
    3. Persist {template_id: {description, embedding, source}}.

Run from project root:
    venv\\Scripts\\python.exe scripts\\build_embeddings.py
"""

from __future__ import annotations

import json
import os
import sys
import time

# Allow `python scripts\\build_embeddings.py` from project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from PIL import Image
from dotenv import load_dotenv
from google import genai
from google.genai import types

import app  # reuses constants + paths

load_dotenv()

EMBED_MODEL = "gemini-embedding-001"
VISION_MODEL = "gemini-2.5-flash"
OUT_PATH = os.path.join(PROJECT_ROOT, "static", "template_embeddings.json")


def describe_image(client: genai.Client, image_path: str, hint: str) -> str:
    img = Image.open(image_path).convert("RGB")
    img.thumbnail((512, 512))
    prompt = (
        f"This is a meme template called '{hint}'. In 2-3 sentences describe: "
        "the mood/emotion conveyed, the visible characters or scene, and what "
        "kind of joke or topic this template works best for. Be concise and "
        "concrete. No preamble."
    )
    resp = client.models.generate_content(
        model=VISION_MODEL,
        contents=[prompt, img],
    )
    return (resp.text or "").strip()


def metadata_text(meta: dict) -> str:
    parts = [
        f"Meme name: {meta.get('name', '')}.",
        f"Format: {meta.get('format', 'single')}.",
    ]
    if meta.get("emotions"):
        parts.append("Emotions: " + ", ".join(meta["emotions"]) + ".")
    if meta.get("use_cases"):
        parts.append("Use cases: " + "; ".join(meta["use_cases"]) + ".")
    if meta.get("caption_style"):
        parts.append("Style: " + meta["caption_style"])
    return " ".join(parts)


def embed_texts(client: genai.Client, texts: list[str]) -> list[list[float]]:
    """One-by-one embed (free tier is 100 RPM); throttle + retry on 429."""
    out: list[list[float]] = []
    for i, text in enumerate(texts):
        attempt = 0
        while True:
            try:
                resp = client.models.embed_content(
                    model=EMBED_MODEL,
                    contents=text,
                    config=types.EmbedContentConfig(
                        task_type="RETRIEVAL_DOCUMENT"
                    ),
                )
                out.append(resp.embeddings[0].values)
                if i % 10 == 0:
                    print(f"  embedded {i + 1}/{len(texts)}")
                time.sleep(0.7)  # ~85 RPM, under the 100 limit
                break
            except Exception as e:
                attempt += 1
                msg = str(e)
                if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                    wait = min(60, 12 * attempt)
                    print(f"  rate-limited, sleeping {wait}s then retrying...")
                    time.sleep(wait)
                    if attempt >= 5:
                        raise
                    continue
                raise
    return out


def _checkpoint(out: dict) -> None:
    tmp = OUT_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f)
    os.replace(tmp, OUT_PATH)


def main() -> None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        sys.exit("GEMINI_API_KEY missing")

    client = genai.Client(api_key=api_key)
    pool = app._all_templates()
    out: dict[str, dict] = (
        json.load(open(OUT_PATH)) if os.path.exists(OUT_PATH) else {}
    )
    todo = [(tid, meta) for tid, meta in pool.items()
            if not (out.get(tid) or {}).get("embedding")]
    print(f"Templates total: {len(pool)}; already cached: {len(pool) - len(todo)}; "
          f"to do: {len(todo)}")

    for idx, (tid, meta) in enumerate(todo, 1):
        # Step 1: description
        try:
            if meta.get("source") == "imgflip":
                path = app.template_image_path(tid, meta)
                desc = describe_image(client, path, meta.get("name", tid))
                description = f"{metadata_text(meta)} Visual: {desc}"
                source = "vision"
            else:
                description = metadata_text(meta)
                source = "metadata"
        except Exception as e:
            print(f"  [desc-err] {tid}: {e}")
            description = metadata_text(meta)
            source = "metadata_fallback"

        # Step 2: embed (with retry)
        attempt = 0
        embedding: list[float] | None = None
        while attempt < 6:
            try:
                resp = client.models.embed_content(
                    model=EMBED_MODEL,
                    contents=description,
                    config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
                )
                embedding = resp.embeddings[0].values
                break
            except Exception as e:
                msg = str(e)
                if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                    wait = min(60, 12 * (attempt + 1))
                    print(f"  [{idx}/{len(todo)}] rate-limited, sleeping {wait}s")
                    time.sleep(wait)
                    attempt += 1
                    continue
                print(f"  [embed-err] {tid}: {e}")
                break

        if embedding is None:
            print(f"  [skip] {tid}")
            continue

        out[tid] = {"description": description, "source": source, "embedding": embedding}
        _checkpoint(out)
        if idx % 5 == 0 or idx == len(todo):
            print(f"  [{idx}/{len(todo)}] {tid[:40]} ({source})")
        time.sleep(0.7)  # throttle to stay under RPM

    size_kb = os.path.getsize(OUT_PATH) / 1024
    print(f"\n[done] {len(out)} embeddings -> {OUT_PATH} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
