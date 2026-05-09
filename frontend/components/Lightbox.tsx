"use client"

import { motion, AnimatePresence } from "framer-motion"
import { Download, X } from "lucide-react"
import { useEffect } from "react"
import { absoluteUrl } from "@/lib/api"

export default function Lightbox({
  url,
  onClose,
}: {
  url: string | null
  onClose: () => void
}) {
  useEffect(() => {
    if (!url) return
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose()
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [url, onClose])

  return (
    <AnimatePresence>
      {url && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 z-[100] bg-black/80 backdrop-blur-md grid place-items-center p-4"
        >
          <motion.div
            initial={{ scale: 0.95, y: 20 }}
            animate={{ scale: 1, y: 0 }}
            exit={{ scale: 0.95, y: 10 }}
            transition={{ type: "spring", stiffness: 240, damping: 26 }}
            onClick={(e) => e.stopPropagation()}
            className="relative max-w-4xl w-full"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={absoluteUrl(url)}
              alt="meme"
              className="rounded-3xl w-full max-h-[85vh] object-contain bg-black/40"
            />
            <div className="absolute -top-3 -right-3 flex gap-2">
              <a
                href={absoluteUrl(url)}
                download
                className="p-2 rounded-full bg-white text-black shadow-lg"
                title="Download"
              >
                <Download className="w-4 h-4" />
              </a>
              <button
                onClick={onClose}
                className="p-2 rounded-full bg-white text-black shadow-lg"
                title="Close"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
