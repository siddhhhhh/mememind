import { API_BASE } from "./config"

export type Mode = "smart" | "fresh" | "upload" | "comic"

export type Analysis = {
  sentiment: string
  tone: string
  emotion: string
  cultural_context: string
  keywords: string[]
}

export type TemplateRef = {
  id: string
  name: string
  format: string
  source?: string
}

export type JudgeCandidate = {
  captions: Record<string, string>
  score: number
  humor: number
  relevance: number
  fit: number
  reason: string
}

export type JudgeData = {
  winner_score: number
  winner_reason: string
  candidates_total: number
  all: JudgeCandidate[]
}

export type GenerateResult = {
  mode: Mode
  url: string
  topic: string
  template?: TemplateRef
  captions: Record<string, string>
  analysis: Analysis
  retrieval?: "rag" | "keyword" | "explicit"
  judge?: JudgeData | null
}

export type Variant = {
  url: string
  template: TemplateRef
  captions: Record<string, string>
}

export type VariantsResult = {
  mode: Mode
  topic: string
  analysis: Analysis
  variants: Variant[]
  retrieval?: "rag" | "keyword"
}

export type ComicPanel = {
  title: string
  beat: string
  emotion: string
  caption: string
  template: TemplateRef
  captions: Record<string, string>
}

export type ComicResult = {
  mode: "comic"
  url: string
  topic: string
  analysis: Analysis
  panels: ComicPanel[]
}

export type TemplateCard = {
  id: string
  name: string
  format: string
  emotions: string[]
  use_cases: string[]
  source: "local" | "imgflip"
  url: string
}

export type LatestMeme = { url: string; created_at: number }

export const absoluteUrl = (path: string) =>
  path.startsWith("http") ? path : `${API_BASE}${path}`

const json = <T,>(p: Promise<Response>): Promise<T> =>
  p.then(async (r) => {
    if (!r.ok) {
      const txt = await r.text()
      try {
        const body = JSON.parse(txt)
        const err: any = new Error(body.error || `HTTP ${r.status}`)
        err.fallback = body.fallback
        throw err
      } catch {
        throw new Error(txt || `HTTP ${r.status}`)
      }
    }
    return r.json()
  })

export const api = {
  generate: (topic: string, template_id?: string, judge = true) =>
    json<GenerateResult>(
      fetch(`${API_BASE}/api/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic, template_id, judge }),
      }),
    ),

  generateComic: (topic: string, panels = 3) =>
    json<ComicResult>(
      fetch(`${API_BASE}/api/generate_comic`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic, panels }),
      }),
    ),

  generateVariants: (topic: string, n = 3) =>
    json<VariantsResult>(
      fetch(`${API_BASE}/api/generate_variants`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic, n }),
      }),
    ),

  generateFresh: (topic: string) =>
    json<GenerateResult>(
      fetch(`${API_BASE}/api/generate_fresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic }),
      }),
    ),

  captionUpload: (topic: string, file: File) => {
    const fd = new FormData()
    fd.append("topic", topic)
    fd.append("image", file)
    return json<GenerateResult>(
      fetch(`${API_BASE}/api/caption_upload`, { method: "POST", body: fd }),
    )
  },

  regenerate: (topic: string, template_id: string) =>
    json<GenerateResult>(
      fetch(`${API_BASE}/api/regenerate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic, template_id }),
      }),
    ),

  templates: () => json<TemplateCard[]>(fetch(`${API_BASE}/api/templates`)),
  latest: (limit = 30) =>
    json<LatestMeme[]>(fetch(`${API_BASE}/api/latest?limit=${limit}`)),
  trending: () => json<string[]>(fetch(`${API_BASE}/api/trending`)),
  health: () =>
    json<{
      providers: { groq: boolean; gemini: boolean }
      templates: { local: number; imgflip_cached: number }
    }>(fetch(`${API_BASE}/`)),
}
