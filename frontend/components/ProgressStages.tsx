"use client"

import { motion } from "framer-motion"
import { Brain, Image as ImageIcon, MessageSquare, Layers } from "lucide-react"

export type StageKey = "analyze" | "select" | "caption" | "render"

const stages: { id: StageKey; label: string; Icon: typeof Brain }[] = [
  { id: "analyze", label: "Analyzing topic", Icon: Brain },
  { id: "select", label: "Picking template", Icon: Layers },
  { id: "caption", label: "Writing caption", Icon: MessageSquare },
  { id: "render", label: "Rendering meme", Icon: ImageIcon },
]

export default function ProgressStages({ active }: { active: StageKey | null }) {
  if (!active) return null
  const activeIdx = stages.findIndex((s) => s.id === active)
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-3">
      {stages.map(({ id, label, Icon }, i) => {
        const isDone = i < activeIdx
        const isActive = i === activeIdx
        return (
          <motion.div
            key={id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            className={`relative rounded-2xl p-3 sm:p-4 ring-1 transition-colors ${
              isActive
                ? "bg-white/10 ring-fuchsia-400/40"
                : isDone
                  ? "bg-emerald-500/10 ring-emerald-400/30"
                  : "bg-white/5 ring-white/10"
            }`}
          >
            <div className="flex items-center gap-2">
              <div
                className={`w-7 h-7 grid place-items-center rounded-lg ${
                  isActive
                    ? "bg-fuchsia-500/30 text-fuchsia-200"
                    : isDone
                      ? "bg-emerald-500/30 text-emerald-200"
                      : "bg-white/5 text-white/40"
                }`}
              >
                {isActive ? (
                  <span className="w-3 h-3 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                ) : (
                  <Icon className="w-3.5 h-3.5" />
                )}
              </div>
              <div className="text-xs sm:text-sm font-medium">
                <span
                  className={
                    isActive ? "text-white" : isDone ? "text-emerald-200/90" : "text-white/55"
                  }
                >
                  {label}
                </span>
              </div>
            </div>
            {isActive && (
              <motion.div
                layoutId="progress-bar"
                className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-fuchsia-500 to-amber-300 rounded-b-2xl"
              />
            )}
          </motion.div>
        )
      })}
    </div>
  )
}
