"use client"

import { useEffect, useRef, useState } from "react"
import { AnimatePresence, motion } from "framer-motion"
import {
  Sparkles,
  Wand2,
  Upload,
  ImagePlus,
  ChevronRight,
  Hash,
  BookOpen,
  Trophy,
  Brain,
} from "lucide-react"
import {
  api,
  type Analysis,
  type ComicResult,
  type GenerateResult,
  type Mode,
  type Variant,
  absoluteUrl,
} from "@/lib/api"
import ModeSwitcher from "@/components/ModeSwitcher"
import ProgressStages, { type StageKey } from "@/components/ProgressStages"
import AnalysisChips from "@/components/AnalysisChips"
import MemeResultCard from "@/components/MemeResultCard"

export default function HomePage() {
  const [mode, setMode] = useState<Mode>("smart")
  const [topic, setTopic] = useState("")
  const [file, setFile] = useState<File | null>(null)
  const [filePreview, setFilePreview] = useState<string | null>(null)
  const [variantsMode, setVariantsMode] = useState(true)

  const [stage, setStage] = useState<StageKey | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [single, setSingle] = useState<GenerateResult | null>(null)
  const [variants, setVariants] = useState<Variant[] | null>(null)
  const [comic, setComic] = useState<ComicResult | null>(null)
  const [picked, setPicked] = useState<number>(0)

  const [trending, setTrending] = useState<string[]>([])
  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    api.trending().then(setTrending).catch(() => {})
  }, [])

  useEffect(() => {
    if (!file) return
    const url = URL.createObjectURL(file)
    setFilePreview(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  const reset = () => {
    setSingle(null)
    setVariants(null)
    setComic(null)
    setAnalysis(null)
    setError(null)
    setPicked(0)
  }

  const submit = async () => {
    if (!topic.trim()) return
    if (mode === "upload" && !file) {
      setError("Pick an image to caption (jpg/png/webp).")
      return
    }
    reset()
    setStage("analyze")

    // Fake-but-honest visual progress: we have one network call, but the user
    // sees the underlying stages the backend is actually performing.
    const advance = (s: StageKey, ms: number) =>
      new Promise<void>((res) => setTimeout(() => { setStage(s); res() }, ms))

    try {
      const work = (async () => {
        if (mode === "smart" && variantsMode) {
          return await api.generateVariants(topic.trim(), 3)
        }
        if (mode === "smart") return await api.generate(topic.trim())
        if (mode === "comic") return await api.generateComic(topic.trim(), 3)
        if (mode === "fresh") return await api.generateFresh(topic.trim())
        return await api.captionUpload(topic.trim(), file!)
      })()

      // Visual cadence (each step <1s usually fits real backend timing)
      await advance("select", 700)
      await advance("caption", 700)
      await advance("render", 600)

      const result = await work
      if ("panels" in result) {
        setComic(result)
        setAnalysis(result.analysis)
      } else if ("variants" in result) {
        setVariants(result.variants)
        setAnalysis(result.analysis)
      } else {
        setSingle(result)
        setAnalysis(result.analysis)
      }
      setStage(null)
    } catch (e: any) {
      setError(e?.message || "Something went wrong.")
      setStage(null)
      // If Fresh mode failed and backend suggests fallback, auto-switch to Smart
      if (e?.fallback === "smart" && mode === "fresh") {
        setMode("smart")
      }
    }
  }

  const regenerateCurrent = async () => {
    if (!single?.template) return
    setStage("caption")
    try {
      const r = await api.regenerate(topic.trim(), single.template.id)
      setSingle(r)
    } catch (e: any) {
      setError(e?.message || "Regenerate failed")
    } finally {
      setStage(null)
    }
  }

  const regenerateVariant = async (i: number) => {
    if (!variants) return
    const v = variants[i]
    setStage("caption")
    try {
      const r = await api.regenerate(topic.trim(), v.template.id)
      const next = [...variants]
      next[i] = { url: r.url, template: r.template!, captions: r.captions }
      setVariants(next)
    } catch (e: any) {
      setError(e?.message || "Regenerate failed")
    } finally {
      setStage(null)
    }
  }

  const onPickFile = (f: File | null) => {
    if (!f) return setFile(null)
    if (!/^image\/(jpe?g|png|webp)$/i.test(f.type)) {
      setError("File must be JPG, PNG, or WEBP.")
      return
    }
    setError(null)
    setFile(f)
  }

  return (
    <section className="relative">
      {/* Hero */}
      <div className="relative hero-mesh overflow-hidden">
        <div className="container mx-auto px-4 sm:px-6 pt-12 sm:pt-16 pb-8 sm:pb-12 max-w-5xl">
          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center max-w-3xl mx-auto"
          >
            <div className="inline-flex items-center gap-2 text-xs px-3 py-1.5 rounded-full glass mb-5">
              <Sparkles className="w-3.5 h-3.5 text-amber-300" />
              <span className="text-white/80">
                Topic-aware · Context-rich · 120+ templates
              </span>
            </div>
            <h1 className="text-5xl sm:text-7xl font-black tracking-tight leading-[1.05]">
              <span className="text-aurora">Memes that get</span>
              <br />
              <span className="text-white">the joke for you.</span>
            </h1>
            <p className="text-white/65 mt-5 text-base sm:text-lg max-w-2xl mx-auto">
              Drop a topic — a news headline, a vibe, anything. MemeMind reads the
              emotion, picks the right format, writes the caption, and lays it
              out cleanly. Three modes, one flow.
            </p>
          </motion.div>

          {/* Generator card */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="glass-strong mt-10 rounded-3xl p-4 sm:p-6"
          >
            <ModeSwitcher value={mode} onChange={setMode} />

            <div className="mt-4 grid gap-3">
              <div className="relative">
                <input
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && submit()}
                  placeholder={
                    mode === "fresh"
                      ? "Describe the scene… e.g. 'a cat doing taxes'"
                      : mode === "upload"
                        ? "What's the joke? e.g. 'when the build finally passes'"
                        : mode === "comic"
                          ? "A storyline topic… e.g. 'job interview rounds in 2026'"
                          : "Any topic… e.g. 'AI replacing junior devs'"
                  }
                  className="w-full text-lg sm:text-xl bg-black/30 ring-1 ring-white/10 focus:ring-fuchsia-400/50 focus:outline-none rounded-2xl px-5 py-4 placeholder-white/35"
                />
                <Hash className="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-white/30" />
              </div>

              {mode === "upload" && (
                <UploadDrop
                  preview={filePreview}
                  onPick={onPickFile}
                  fileRef={fileRef}
                />
              )}

              {/* Trending chips */}
              {!!trending.length && mode !== "upload" && mode !== "fresh" && (
                <div className="flex flex-wrap gap-2 pt-1">
                  <span className="text-xs text-white/40 self-center mr-1">
                    Trending:
                  </span>
                  {trending.slice(0, 6).map((t) => (
                    <button
                      key={t}
                      onClick={() => setTopic(t)}
                      className="text-xs px-3 py-1.5 rounded-full bg-white/5 hover:bg-white/10 ring-1 ring-white/10 text-white/80 transition-colors"
                    >
                      {t}
                    </button>
                  ))}
                </div>
              )}

              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pt-2">
                {mode === "smart" ? (
                  <label className="inline-flex items-center gap-2 text-sm text-white/70 select-none cursor-pointer">
                    <input
                      type="checkbox"
                      checked={variantsMode}
                      onChange={(e) => setVariantsMode(e.target.checked)}
                      className="accent-fuchsia-500 w-4 h-4"
                    />
                    Generate 3 variants to choose from
                  </label>
                ) : (
                  <span className="text-xs text-white/40">
                    {mode === "fresh"
                      ? "Gemini 2.5 Flash Image will generate the background."
                      : mode === "comic"
                        ? "3 panels, narrative arc: setup → escalation → punchline."
                        : "Your image will be captioned with Impact-style overlay."}
                  </span>
                )}
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.97 }}
                  onClick={submit}
                  disabled={
                    !topic.trim() || stage !== null || (mode === "upload" && !file)
                  }
                  className="inline-flex items-center justify-center gap-2 rounded-2xl px-6 py-3 font-bold text-black bg-gradient-to-r from-fuchsia-500 via-pink-400 to-amber-300 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg ring-1 ring-white/30"
                >
                  {mode === "fresh" ? (
                    <Wand2 className="w-4 h-4" />
                  ) : mode === "upload" ? (
                    <Upload className="w-4 h-4" />
                  ) : mode === "comic" ? (
                    <BookOpen className="w-4 h-4" />
                  ) : (
                    <Sparkles className="w-4 h-4" />
                  )}
                  Generate
                  <ChevronRight className="w-4 h-4" />
                </motion.button>
              </div>
            </div>
          </motion.div>

          {/* Progress */}
          <AnimatePresence>
            {stage && (
              <motion.div
                key="progress"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="mt-6"
              >
                <ProgressStages active={stage} />
              </motion.div>
            )}
          </AnimatePresence>

          {error && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="mt-6 text-sm text-red-300 bg-red-500/10 ring-1 ring-red-500/30 rounded-2xl px-4 py-3"
            >
              {error}
            </motion.div>
          )}
        </div>
      </div>

      {/* Results */}
      <div className="container mx-auto px-4 sm:px-6 max-w-5xl pb-16">
        {analysis && (
          <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass rounded-3xl p-4 sm:p-5 mt-6"
          >
            <div className="flex items-center gap-2 mb-3 flex-wrap">
              <Sparkles className="w-4 h-4 text-fuchsia-400" />
              <span className="text-sm font-semibold text-white/80">
                Topic analysis
              </span>
              {single?.retrieval === "rag" && (
                <span className="ml-auto inline-flex items-center gap-1 text-[10px] uppercase tracking-wider px-2 py-1 rounded-full bg-cyan-500/15 text-cyan-200 ring-1 ring-cyan-400/30">
                  <Brain className="w-3 h-3" /> Picked via vision-RAG
                </span>
              )}
              {single?.judge?.winner_score != null && (
                <span className="inline-flex items-center gap-1 text-[10px] uppercase tracking-wider px-2 py-1 rounded-full bg-amber-500/15 text-amber-200 ring-1 ring-amber-400/30">
                  <Trophy className="w-3 h-3" /> Judge: {single.judge.winner_score.toFixed(1)}/10
                </span>
              )}
            </div>
            <AnalysisChips data={analysis} />
          </motion.div>
        )}

        {single && (
          <div className="mt-6 grid sm:grid-cols-[1fr_320px] gap-4">
            <MemeResultCard
              url={single.url}
              title={single.template?.name}
              subtitle={
                single.template
                  ? `${single.template.format} · ${single.template.source ?? "local"}`
                  : single.mode
              }
              badge={single.mode === "fresh" ? "AI generated" : single.mode}
              onRegenerate={
                single.template ? regenerateCurrent : undefined
              }
              highlight
            />
            <div className="space-y-3">
              <CaptionsPanel captions={single.captions} />
              {single.judge && single.judge.all.length > 1 && (
                <JudgePanel judge={single.judge} />
              )}
            </div>
          </div>
        )}

        {comic && (
          <div className="mt-6 space-y-4">
            <div className="flex items-center gap-2 flex-wrap">
              <BookOpen className="w-4 h-4 text-fuchsia-400" />
              <h3 className="text-xl font-bold">{comic.panels.length}-panel comic</h3>
              <span className="text-xs text-white/40">
                Setup → Escalation → Punchline
              </span>
            </div>
            <div className="grid lg:grid-cols-[1fr_320px] gap-4">
              <MemeResultCard
                url={comic.url}
                title="Multi-panel meme"
                subtitle={`${comic.panels.length} panels · narrative arc`}
                badge="comic"
                highlight
              />
              <ComicPanelsList panels={comic.panels} />
            </div>
          </div>
        )}

        {variants && variants.length > 0 && (
          <>
            <div className="mt-8 mb-3 flex items-end justify-between">
              <h3 className="text-xl font-bold">
                Pick your favorite{" "}
                <span className="text-white/40 text-sm font-normal">
                  ({variants.length} variants)
                </span>
              </h3>
              <button
                onClick={() => regenerateVariant(picked)}
                className="text-xs text-white/60 hover:text-white"
              >
                Regenerate selected
              </button>
            </div>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {variants.map((v, i) => (
                <button
                  key={v.url}
                  onClick={() => setPicked(i)}
                  className="text-left"
                >
                  <MemeResultCard
                    url={v.url}
                    title={v.template.name}
                    subtitle={`${v.template.format} · ${v.template.source ?? "local"}`}
                    badge={i === picked ? "selected" : undefined}
                    highlight={i === picked}
                  />
                </button>
              ))}
            </div>
          </>
        )}
      </div>
    </section>
  )
}

function JudgePanel({ judge }: { judge: NonNullable<GenerateResult["judge"]> }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass rounded-3xl p-4 sm:p-5"
    >
      <div className="text-sm font-semibold text-white/80 mb-1 inline-flex items-center gap-2">
        <Trophy className="w-4 h-4 text-amber-300" /> Judge ranked {judge.candidates_total} candidates
      </div>
      <div className="text-[11px] text-white/45 mb-3">{judge.winner_reason}</div>
      <div className="space-y-2">
        {judge.all.slice(0, 5).map((c, i) => (
          <div
            key={i}
            className={`rounded-xl px-3 py-2 ring-1 ${
              i === 0
                ? "bg-amber-500/10 ring-amber-400/30"
                : "bg-black/30 ring-white/10"
            }`}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-[10px] uppercase tracking-wider text-white/45">
                #{i + 1}
              </span>
              <span className="text-xs font-semibold text-white">
                {c.score.toFixed(1)}
              </span>
            </div>
            <div className="text-xs text-white/85 mt-1">
              {Object.values(c.captions).filter(Boolean).join(" · ")}
            </div>
            {c.reason && i === 0 && (
              <div className="text-[10px] text-amber-200/80 mt-1 italic">
                {c.reason}
              </div>
            )}
          </div>
        ))}
      </div>
    </motion.div>
  )
}

function ComicPanelsList({
  panels,
}: {
  panels: ComicResult["panels"]
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass rounded-3xl p-4 sm:p-5"
    >
      <div className="text-sm font-semibold text-white/80 mb-3">Story beats</div>
      <ol className="space-y-3">
        {panels.map((p, i) => (
          <li key={i} className="rounded-xl bg-black/30 ring-1 ring-white/10 p-3">
            <div className="flex items-center justify-between">
              <span className="text-[10px] uppercase tracking-wider text-fuchsia-300">
                Panel {i + 1} · {p.title}
              </span>
              <span className="text-[10px] text-white/40">{p.template.name}</span>
            </div>
            <div className="text-xs text-white/70 mt-1">{p.beat}</div>
            <div className="text-xs text-white/95 mt-2 font-semibold">
              "{p.caption}"
            </div>
          </li>
        ))}
      </ol>
    </motion.div>
  )
}

function CaptionsPanel({ captions }: { captions: Record<string, string> }) {
  return (
    <div className="glass rounded-3xl p-4 sm:p-5">
      <div className="text-sm font-semibold text-white/80 mb-3">Caption</div>
      <div className="space-y-2">
        {Object.entries(captions).map(([k, v]) => (
          <div
            key={k}
            className="rounded-xl bg-black/30 ring-1 ring-white/10 px-3 py-2"
          >
            <div className="text-[10px] uppercase tracking-wider text-white/40">
              {k}
            </div>
            <div className="text-sm text-white/90">{v || "—"}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

function UploadDrop({
  preview,
  onPick,
  fileRef,
}: {
  preview: string | null
  onPick: (f: File | null) => void
  fileRef: React.RefObject<HTMLInputElement | null>
}) {
  return (
    <div
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => {
        e.preventDefault()
        const f = e.dataTransfer.files?.[0]
        if (f) onPick(f)
      }}
      className="glass rounded-2xl p-4 flex items-center gap-4 cursor-pointer"
      onClick={() => fileRef.current?.click()}
    >
      <input
        ref={fileRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        onChange={(e) => onPick(e.target.files?.[0] || null)}
      />
      <div className="w-16 h-16 rounded-xl bg-black/40 ring-1 ring-white/10 grid place-items-center overflow-hidden">
        {preview ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={preview} alt="preview" className="w-full h-full object-cover" />
        ) : (
          <ImagePlus className="w-6 h-6 text-white/40" />
        )}
      </div>
      <div className="text-sm">
        <div className="font-semibold">
          {preview ? "Image ready" : "Drop an image or click to upload"}
        </div>
        <div className="text-white/50 text-xs">JPG / PNG / WEBP, up to 10MB</div>
      </div>
    </div>
  )
}
