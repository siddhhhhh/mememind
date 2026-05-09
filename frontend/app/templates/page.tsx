"use client"

import { useEffect, useMemo, useState } from "react"
import { motion } from "framer-motion"
import { Layers, Search } from "lucide-react"
import { absoluteUrl, api, type TemplateCard } from "@/lib/api"
import Lightbox from "@/components/Lightbox"

export default function TemplatesPage() {
  const [items, setItems] = useState<TemplateCard[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [q, setQ] = useState("")
  const [source, setSource] = useState<"all" | "local" | "imgflip">("all")
  const [open, setOpen] = useState<string | null>(null)

  useEffect(() => {
    api
      .templates()
      .then((t) => setItems(t))
      .catch((e) => setError(e?.message || "Failed to load"))
      .finally(() => setLoading(false))
  }, [])

  const filtered = useMemo(() => {
    const term = q.trim().toLowerCase()
    return items.filter((t) => {
      if (source !== "all" && t.source !== source) return false
      if (!term) return true
      const blob =
        t.name.toLowerCase() +
        " " +
        t.emotions.join(" ") +
        " " +
        t.use_cases.join(" ")
      return blob.includes(term)
    })
  }, [items, q, source])

  const counts = useMemo(() => {
    const local = items.filter((i) => i.source === "local").length
    return { all: items.length, local, imgflip: items.length - local }
  }, [items])

  return (
    <section className="container mx-auto px-4 sm:px-6 py-12 max-w-6xl">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <div className="inline-flex items-center gap-2 text-xs px-3 py-1.5 rounded-full glass mb-3">
          <Layers className="w-3.5 h-3.5 text-cyan-300" />
          <span className="text-white/80">
            {counts.local} local + {counts.imgflip} imgflip = {counts.all}{" "}
            templates
          </span>
        </div>
        <h1 className="text-4xl sm:text-5xl font-black tracking-tight">
          <span className="text-aurora">Template library</span>
        </h1>
        <p className="text-white/60 mt-2">
          Browse every meme format. Search by name, emotion, or use case.
        </p>
      </motion.div>

      <div className="glass rounded-3xl p-3 sm:p-4 mb-6 flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search templates… 'drake', 'confused', 'preference'"
            className="w-full pl-10 pr-3 py-2.5 rounded-xl bg-black/30 ring-1 ring-white/10 focus:ring-fuchsia-400/50 focus:outline-none text-sm"
          />
        </div>
        <div className="flex items-center gap-1">
          {(["all", "local", "imgflip"] as const).map((s) => (
            <button
              key={s}
              onClick={() => setSource(s)}
              className={`text-xs px-3 py-2 rounded-xl ring-1 ring-white/10 transition-colors ${
                source === s
                  ? "bg-white/10 text-white"
                  : "bg-transparent text-white/55 hover:text-white"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="text-sm text-red-300 bg-red-500/10 ring-1 ring-red-500/30 rounded-2xl px-4 py-3 mb-6">
          {error}
        </div>
      )}

      {loading ? (
        <Skeleton />
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {filtered.map((t, i) => (
            <motion.button
              key={t.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: Math.min(i * 0.02, 0.5) }}
              whileHover={{ y: -4 }}
              onClick={() => setOpen(t.url)}
              className="glass rounded-2xl overflow-hidden text-left group"
            >
              <div className="aspect-square bg-black/40 overflow-hidden">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={absoluteUrl(t.url)}
                  alt={t.name}
                  loading="lazy"
                  className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                />
              </div>
              <div className="p-3">
                <div className="text-sm font-semibold truncate">{t.name}</div>
                <div className="flex items-center gap-1 mt-1">
                  <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-white/5 text-white/55">
                    {t.source}
                  </span>
                  <span className="text-[10px] text-white/45 truncate">
                    {t.emotions.slice(0, 2).join(" · ")}
                  </span>
                </div>
              </div>
            </motion.button>
          ))}
          {filtered.length === 0 && (
            <div className="col-span-full text-center text-white/55 py-16 glass rounded-3xl">
              No templates match.
            </div>
          )}
        </div>
      )}

      <Lightbox url={open} onClose={() => setOpen(null)} />
    </section>
  )
}

function Skeleton() {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
      {Array.from({ length: 12 }).map((_, i) => (
        <div key={i} className="rounded-2xl shimmer aspect-[3/4]" />
      ))}
    </div>
  )
}
