"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import MemeCard from "@/components/MemeCard"
import { API_BASE } from "@/lib/config"

export default function OGTemplates() {
  const [templates, setTemplates] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchOGTemplates = async () => {
      try {
        const response = await fetch(`${API_BASE}/get_og_memes`)
        if (!response.ok) {
          throw new Error("Failed to fetch OG templates")
        }
        const data = await response.json()
        setTemplates(data)
      } catch (err) {
        setError("Failed to load OG templates. Please try again.")
        console.error("Error fetching OG templates:", err)
      } finally {
        setIsLoading(false)
      }
    }

    fetchOGTemplates()
  }, [])

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-16">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500 mx-auto mb-4"></div>
          <p className="text-xl text-gray-600">Loading OG templates...</p>
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
          OG Templates 📸
        </h1>
        <p className="text-xl text-gray-600">Classic meme templates that started it all</p>
      </motion.div>

      {templates.length === 0 ? (
        <div className="text-center">
          <p className="text-xl text-gray-600">No templates available yet.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {templates.map((template, index) => (
            <motion.div
              key={template}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
            >
              <MemeCard src={template} alt={`OG template ${index + 1}`} />
            </motion.div>
          ))}
        </div>
      )}
    </div>
  )
}
