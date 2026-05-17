# MemeMind

Topic-aware meme generator. Type any idea, get a captioned meme back in ~2 seconds.

Four generation modes, two LLM providers with fallback, RAG-based template retrieval over 120+ templates, and an offline eval harness with measured retrieval numbers.

---

## What it does

| Mode | What happens |
|------|--------------|
| **Smart** | RAG retrieves the best-fitting template from 120+ → LLM writes 5 caption candidates → LLM-as-judge picks the winner → render with PIL |
| **Comic** | LLM writes a 3-panel Setup → Escalation → Punchline arc, each panel uses its own template |
| **Fresh** | Gemini 2.5 Flash Image generates a brand-new background, then we overlay an AI caption |
| **Upload** | User uploads any image, backend writes a caption fitted to it |

---

## Architecture

```
┌──────────┐    ┌──────────────────────────────────────────────────────┐
│ Next.js  │───►│  Flask API (app.py)                                  │
│ (React)  │    │                                                      │
└──────────┘    │   topic ──► analyze_topic ──► pick_template ──► caption ──► render
                │              (Groq LLM)        │                │
                │                                │                ├── write_captions_n (5 candidates)
                │                                │                └── judge_captions   (LLM-as-judge)
                │                                │
                │                ┌───────────────┴────────────────┐
                │                │  RAG retrieval (hybrid)        │
                │                │   1. embed query (Gemini)      │
                │                │   2. cosine vs 123 embeddings  │
                │                │   3. + emotion bonus           │
                │                │   4. (opt) LLM reranker top-20 │
                │                └────────────────────────────────┘
                └──────────────────────────────────────────────────────┘
```

### Provider stack

- **Text LLM**: Groq `llama-3.3-70b-versatile` (primary, ~600ms) → Gemini 2.5 Flash (fallback)
- **Embeddings**: Gemini `gemini-embedding-001` (3072-dim, L2-normalised)
- **Image gen**: Gemini 2.5 Flash Image ("Nano Banana") for Fresh mode

All providers degrade gracefully — if Groq is down captions fall through to Gemini; if Gemini-Image is over quota Fresh mode returns a 502 with `fallback: "smart"` and the frontend auto-retries on Smart mode.

---

## Retrieval evaluation

`scripts/eval.py` runs five rankers over a curated 56-topic test set with expected emotions and ideal templates per topic. Metrics: emotion-overlap@k (top-k contains a template whose emotions intersect expected), template-hit@k (top-k contains a hand-picked ideal template), MRR.

| Ranker            | emo@1 | emo@3 | emo@5 | tpl@1 | tpl@3 | tpl@5 | MRR   |
|-------------------|------:|------:|------:|------:|------:|------:|------:|
| **rag_reranked**  | **71.4%** | **82.1%** | **83.9%** | **53.6%** | **66.1%** | **71.4%** | **0.770** |
| rag_hybrid (prod) | 67.9% | 71.4% | 82.1% | 28.6% | 60.7% | 69.6% | 0.728 |
| rag_only          | 39.3% | 57.1% | 69.6% | 19.6% | 50.0% | 58.9% | 0.508 |
| keyword_analysis  | 67.9% | 69.6% | 69.6% | 50.0% | 57.1% | 57.1% | 0.688 |
| keyword_naive     | 23.2% | 32.1% | 33.9% | 19.6% | 28.6% | 30.4% | 0.280 |

**Headline:** Token-overlap baseline → retriever + LLM reranker lifts top-1 template accuracy **23% → 71%** and MRR **0.28 → 0.77**. Layering an LLM reranker on top of the hybrid retriever lifts top-1 template precision a further **+25pp (29% → 54%)**.

Reproduce:
```bash
venv\Scripts\python.exe scripts\eval.py
```

Enable the reranker in production by setting `USE_RERANKER=1` (adds ~400ms per request).

### Caption prompt A/B harness

`scripts/prompt_ab.py` runs two caption-writing prompts (control vs. treatment) on the same retrieved templates and judges all candidates in a single pooled call (controls for judge-baseline drift). Reports mean humor / relevance / fit / overall per variant.

```bash
venv\Scripts\python.exe scripts\prompt_ab.py --limit 20 --n 4
```

### Observability

Every Groq + Gemini call is recorded to `static/telemetry.jsonl` (provider, model, op, latency, tokens, success). Inspect:

```bash
venv\Scripts\python.exe scripts\telemetry_summary.py
venv\Scripts\python.exe scripts\telemetry_summary.py --since 24h
```

Outputs a per-(provider, model, op) table with P50/P95 latency, total tokens, and estimated USD spend.

---

## Setup

### Backend (Flask)

```bash
python -m venv venv
venv\Scripts\activate           # Windows
# or: source venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
```

Create `.env`:
```
GROQ_API_KEY=...
GEMINI_API_KEY=...
USE_RERANKER=0                  # set to 1 for slower but more accurate retrieval
```

Build template embeddings (one-time, ~5 min):
```bash
venv\Scripts\python.exe scripts\build_embeddings.py
```

Run:
```bash
venv\Scripts\python.exe app.py
# Flask on http://127.0.0.1:5000
```

### Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
# Next.js on http://127.0.0.1:3000
```

---

## API

| Endpoint | Body | Returns |
|----------|------|---------|
| `POST /api/analyze` | `{topic}` | analysis JSON (sentiment, tone, emotion, keywords) |
| `POST /api/generate` | `{topic}` | meme URL + template + captions + analysis |
| `POST /api/generate_variants` | `{topic, n}` | top-N caption candidates judged + scored |
| `POST /api/generate_comic` | `{topic, n_panels}` | multi-panel comic strip |
| `POST /api/generate_fresh` | `{topic}` | Gemini-generated background + caption |
| `POST /api/caption_upload` | image multipart + `topic` | user image + AI caption |
| `POST /api/regenerate` | `{topic, template_id}` | new captions for the same template |
| `GET  /api/templates` | — | merged local + imgflip template list |
| `GET  /api/latest` | — | recently generated memes |

---

## Repo layout

```
app.py                            # Flask backend; all generation logic
requirements.txt
static/
  templates_meta.json             # 23 hand-curated local templates
  imgflip_meta.json               # 100 Imgflip templates (auto-derived metadata)
  template_embeddings.json        # 123 × 3072-dim embeddings (RAG corpus)
  meme_templates/                 # local template images
  imgflip_cache/                  # downloaded imgflip images
  latest_memes/                   # generated meme outputs
telemetry.py                      # provider-call recorder (latency + tokens, JSONL)
scripts/
  build_embeddings.py             # one-shot: vision-describe + embed all templates
  eval.py                         # 5-ranker offline retrieval eval
  eval_set.json                   # 56 curated (topic, expected_emotions, ideal_templates)
  eval_results.json               # per-case rankings + aggregate metrics
  prompt_ab.py                    # A/B harness for caption-writing prompts
  telemetry_summary.py            # P50/P95 latency + cost report from telemetry.jsonl
frontend/                         # Next.js 15 + React 19 + TypeScript + Tailwind
```

---

## Tech stack

- **Backend**: Flask 3, NumPy, Pillow, Groq SDK, Google GenAI SDK
- **Frontend**: Next.js 15 (App Router), React 19, TypeScript, TailwindCSS, Framer Motion
- **Models**: Groq Llama 3.3 70B Versatile, Gemini 2.5 Flash, Gemini 2.5 Flash Image, Gemini Embedding 001
