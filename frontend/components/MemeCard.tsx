"use client"

import { motion } from "framer-motion"
import Image from "next/image"
import { API_BASE } from "@/lib/config"

interface MemeCardProps {
  src: string
  alt: string
  className?: string
}

export default function MemeCard({ src, alt, className = "" }: MemeCardProps) {
  // ✅ Normalize src: if backend already gives full URL, use it as-is
  const imageUrl = src.startsWith("http") ? src : `${API_BASE}${src}`

  const handleDownload = async () => {
    try {
      const response = await fetch(imageUrl)
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `meme-${Date.now()}.jpg`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      console.error("Download failed:", error)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ scale: 1.02, y: -5 }}
      className={`bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl overflow-hidden border border-purple-200 ${className}`}
    >
      {/* 👇 Meme Preview */}
      <div className="relative aspect-square">
        <Image
          src={imageUrl}
          alt={alt}
          fill
          className="object-contain"
          sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
        />
      </div>

      {/* 👇 Download Button */}
      <div className="p-4">
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={handleDownload}
          className="w-full bg-gradient-to-r from-purple-500 to-pink-500 text-white font-semibold py-2 px-4 rounded-xl hover:from-purple-600 hover:to-pink-600 transition-all shadow-lg"
        >
          📥 Download
        </motion.button>
      </div>
    </motion.div>
  )
}
