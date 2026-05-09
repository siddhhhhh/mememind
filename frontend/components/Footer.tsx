"use client"

import { motion } from "framer-motion"
import { Github, Sparkles } from "lucide-react"

export default function Footer() {
  const year = new Date().getFullYear()
  return (
    <motion.footer
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.2 }}
      className="mt-20"
    >
      <div className="container mx-auto px-4 sm:px-6">
        <div className="glass rounded-3xl p-6 sm:p-8 mb-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Sparkles className="w-5 h-5 text-fuchsia-400" />
            <p className="text-sm text-white/70">
              © {year} <span className="font-semibold text-white">MemeMind</span> · Built with
              Groq + Gemini · Hackathon edition
            </p>
          </div>
          <a
            href="https://github.com"
            target="_blank"
            rel="noreferrer"
            className="text-white/60 hover:text-white inline-flex items-center gap-2 text-sm"
          >
            <Github className="w-4 h-4" /> Source
          </a>
        </div>
      </div>
    </motion.footer>
  )
}
