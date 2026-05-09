"use client"

import { useEffect, useState } from "react"
import { motion } from "framer-motion"
import { Flame, RefreshCw } from "lucide-react"
import { absoluteUrl, api, type LatestMeme } from "@/lib/api"
import Lightbox from "@/components/Lightbox"

export default function LatestPage() {
  const [memes, setMemes] = useState<LatestMeme[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [open, setOpen] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const m = await api.latest(60)
      setMemes(m)
    } catch (e: any) {
      setError(e?.message || "Failed to load")
    } finally {
      setLoading(false)
    }
  }
  useEffect(() => {
    load()
  }, [])

  return (
    <section className="container mx-auto px-4 sm:px-6 py-12 max-w-6xl">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8 flex items-end justify-between flex-wrap gap-4"
      >
        <div>
          <div className="inline-flex items-center gap-2 text-xs px-3 py-1.5 rounded-full glass mb-3">
            <Flame className="w-3.5 h-3.5 text-amber-300" />
            <span className="text-white/80">Fresh from the kitchen</span>
          </div>
          <h1 className="text-4xl sm:text-5xl font-black tracking-tight">
            <span className="text-aurora">Latest memes</span>
          </h1>
          <p className="text-white/60 mt-2">
            The most recent generations, refreshed in real time.
          </p>
        </div>
        <button
          onClick={load}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-2xl glass hover:bg-white/10 text-sm"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </motion.div>

      {error && (
        <div className="text-sm text-red-300 bg-red-500/10 ring-1 ring-red-500/30 rounded-2xl px-4 py-3 mb-6">
          {error}
        </div>
      )}

      {loading && memes.length === 0 ? (
        <MasonrySkeleton />
      ) : memes.length === 0 ? (
        <div className="text-center text-white/60 py-20 glass rounded-3xl">
          No memes yet. Generate the first one!
        </div>
      ) : (
        <div className="columns-1 sm:columns-2 lg:columns-3 gap-4 [column-fill:_balance]">
          {memes.map((m, i) => (
            <motion.button
              key={m.url}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: Math.min(i * 0.03, 0.6) }}
              whileHover={{ y: -4 }}
              onClick={() => setOpen(m.url)}
              className="block w-full mb-4 break-inside-avoid glass rounded-2xl overflow-hidden text-left group"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={absoluteUrl(m.url)}
                alt="meme"
                loading="lazy"
                className="w-full h-auto block transition-transform duration-300 group-hover:scale-[1.02]"
              />
              <div className="px-3 py-2 text-[11px] text-white/45">
                {new Date(m.created_at * 1000).toLocaleString()}
              </div>
            </motion.button>
          ))}
        </div>
      )}

      <Lightbox url={open} onClose={() => setOpen(null)} />
    </section>
  )
}

function MasonrySkeleton() {
  return (
    <div className="columns-1 sm:columns-2 lg:columns-3 gap-4">
      {Array.from({ length: 9 }).map((_, i) => (
        <div
          key={i}
          className="mb-4 break-inside-avoid rounded-2xl shimmer"
          style={{ height: 200 + (i % 3) * 80 }}
        />
      ))}
    </div>
  )
}
