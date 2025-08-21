"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import MemeCard from "@/components/MemeCard"
import { API_BASE } from "@/lib/config"

export default function LatestMemes() {
  const [memes, setMemes] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchLatestMemes = async () => {
      try {
        const response = await fetch(`${API_BASE}/get_latest_memes`)
        if (!response.ok) {
          throw new Error("Failed to fetch latest memes")
        }
        const data = await response.json()
        setMemes(data)
      } catch (err) {
        setError("Failed to load latest memes. Please try again.")
        console.error("Error fetching latest memes:", err)
      } finally {
        setIsLoading(false)
      }
    }

    fetchLatestMemes()
  }, [])

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-16">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500 mx-auto mb-4"></div>
          <p className="text-xl text-gray-600">Loading latest memes...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-16">
        <div className="text-center">
          <p className="text-xl text-red-600">{error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-16">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-12">
        <h1 className="text-5xl font-black mb-6 bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
          Latest Memes 🔥
        </h1>
        <p className="text-xl text-gray-600">Check out the most recently generated memes</p>
      </motion.div>

      {memes.length === 0 ? (
        <div className="text-center">
          <p className="text-xl text-gray-600">No memes generated yet. Be the first!</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {memes.map((meme, index) => (
            <motion.div
              key={meme}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
            >
              <MemeCard src={meme} alt={`Latest meme ${index + 1}`} />
            </motion.div>
          ))}
        </div>
      )}
    </div>
  )
}
