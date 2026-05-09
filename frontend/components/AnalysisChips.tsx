"use client"

import { motion } from "framer-motion"
import type { Analysis } from "@/lib/api"

const tone = (t: string) => {
  const map: Record<string, string> = {
    sarcastic: "from-fuchsia-500/30 to-pink-500/20",
    wholesome: "from-emerald-500/30 to-lime-400/20",
    absurd: "from-amber-400/30 to-orange-500/20",
    edgy: "from-rose-500/30 to-red-500/20",
    relatable: "from-sky-500/30 to-cyan-400/20",
    ironic: "from-violet-500/30 to-indigo-500/20",
  }
  return map[t] || "from-white/10 to-white/5"
}

export default function AnalysisChips({ data }: { data: Analysis }) {
  const items: { label: string; value: string; cls?: string }[] = [
    { label: "tone", value: data.tone, cls: tone(data.tone) },
    { label: "emotion", value: data.emotion },
    { label: "sentiment", value: data.sentiment },
    ...(data.cultural_context ? [{ label: "context", value: data.cultural_context }] : []),
  ]
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-wrap gap-2"
    >
      {items.map((it) => (
        <span
          key={it.label}
          className={`text-xs px-3 py-1.5 rounded-full ring-1 ring-white/10 bg-gradient-to-r ${
            it.cls || "from-white/10 to-white/5"
          }`}
        >
          <span className="text-white/50 mr-1">{it.label}:</span>
          <span className="text-white/90 font-medium">{it.value}</span>
        </span>
      ))}
      {data.keywords?.length ? (
        <span className="text-xs px-3 py-1.5 rounded-full ring-1 ring-white/10 bg-white/5">
          <span className="text-white/50 mr-1">keywords:</span>
          <span className="text-white/90 font-medium">{data.keywords.join(", ")}</span>
        </span>
      ) : null}
    </motion.div>
  )
}
