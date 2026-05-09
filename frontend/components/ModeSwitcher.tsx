"use client"

import { motion } from "framer-motion"
import { Sparkles, Wand2, Upload, BookOpen } from "lucide-react"
import type { Mode } from "@/lib/api"

const modes: { id: Mode; label: string; sub: string; Icon: typeof Sparkles }[] = [
  { id: "smart", label: "Smart", sub: "RAG + Judge over 120+ templates", Icon: Sparkles },
  { id: "comic", label: "Comic", sub: "3-panel narrative meme", Icon: BookOpen },
  { id: "fresh", label: "Fresh", sub: "AI generates the image", Icon: Wand2 },
  { id: "upload", label: "Upload", sub: "Caption your own image", Icon: Upload },
]

export default function ModeSwitcher({
  value,
  onChange,
}: {
  value: Mode
  onChange: (m: Mode) => void
}) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-3 p-2 glass rounded-3xl">
      {modes.map(({ id, label, sub, Icon }) => {
        const active = value === id
        return (
          <button
            key={id}
            onClick={() => onChange(id)}
            className="relative rounded-2xl p-3 sm:p-4 text-left transition-colors group"
          >
            {active && (
              <motion.div
                layoutId="mode-pill"
                className="absolute inset-0 rounded-2xl bg-gradient-to-br from-fuchsia-500/30 via-pink-500/20 to-amber-300/20 ring-1 ring-white/20"
                transition={{ type: "spring", stiffness: 380, damping: 32 }}
              />
            )}
            <div className="relative flex items-start gap-3">
              <div
                className={`w-9 h-9 grid place-items-center rounded-xl shrink-0 ${
                  active
                    ? "bg-white/15 text-white"
                    : "bg-white/5 text-white/60 group-hover:text-white"
                }`}
              >
                <Icon className="w-4 h-4" />
              </div>
              <div>
                <div
                  className={`font-semibold text-sm sm:text-base ${
                    active ? "text-white" : "text-white/80"
                  }`}
                >
                  {label}
                </div>
                <div className="text-xs text-white/50 hidden sm:block">{sub}</div>
              </div>
            </div>
          </button>
        )
      })}
    </div>
  )
}
