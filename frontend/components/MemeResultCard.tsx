"use client"

import { motion } from "framer-motion"
import { Download, RotateCcw } from "lucide-react"
import { absoluteUrl } from "@/lib/api"

export default function MemeResultCard({
  url,
  title,
  subtitle,
  badge,
  onRegenerate,
  highlight,
}: {
  url: string
  title?: string
  subtitle?: string
  badge?: string
  onRegenerate?: () => void
  highlight?: boolean
}) {
  const full = absoluteUrl(url)
  const download = async () => {
    try {
      const r = await fetch(full)
      const blob = await r.blob()
      const a = document.createElement("a")
      a.href = URL.createObjectURL(blob)
      a.download = `mememind-${Date.now()}.jpg`
      document.body.appendChild(a)
      a.click()
      a.remove()
    } catch {
      window.open(full, "_blank")
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: "spring", stiffness: 220, damping: 22 }}
      whileHover={{ y: -4 }}
      className={`glass rounded-3xl overflow-hidden flex flex-col ${
        highlight ? "ring-glow" : ""
      }`}
    >
      <div className="relative bg-black/30">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={full} alt={title || "meme"} className="w-full h-auto block" />
        {badge && (
          <span className="absolute top-3 left-3 text-[10px] uppercase tracking-wider px-2 py-1 rounded-full bg-black/60 ring-1 ring-white/15 text-white/80">
            {badge}
          </span>
        )}
      </div>
      <div className="p-4 flex items-center justify-between gap-3">
        <div className="min-w-0">
          {title && <div className="font-semibold truncate">{title}</div>}
          {subtitle && (
            <div className="text-xs text-white/50 truncate">{subtitle}</div>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {onRegenerate && (
            <button
              onClick={onRegenerate}
              className="p-2 rounded-xl bg-white/5 hover:bg-white/10 ring-1 ring-white/10 text-white/80"
              title="Regenerate caption"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          )}
          <button
            onClick={download}
            className="px-3 py-2 rounded-xl bg-gradient-to-r from-fuchsia-500 to-amber-400 text-black font-semibold inline-flex items-center gap-2"
          >
            <Download className="w-4 h-4" /> Save
          </button>
        </div>
      </div>
    </motion.div>
  )
}
