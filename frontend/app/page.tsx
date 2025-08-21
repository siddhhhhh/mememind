"use client"

import { useState } from "react"
import { motion } from "framer-motion"
import Image from "next/image"
import { API_BASE } from "@/lib/config"

export default function Home() {
  const [topic, setTopic] = useState("")
  const [generatedMeme, setGeneratedMeme] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const generateMeme = async () => {
    if (!topic.trim()) return

    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE}/generate_meme`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ topic }),
      })

      if (!response.ok) {
        throw new Error("Failed to generate meme")
      }

      const blob = await response.blob()
      const imageUrl = URL.createObjectURL(blob)
      setGeneratedMeme(imageUrl)
    } catch (err) {
      setError("Failed to generate meme. Please try again.")
      console.error("Error generating meme:", err)
    } finally {
      setIsLoading(false)
    }
  }

  const downloadMeme = () => {
    if (!generatedMeme) return

    const a = document.createElement("a")
    a.href = generatedMeme
    a.download = `meme-${topic}-${Date.now()}.jpg`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }

  return (
    <div className="container mx-auto px-4 py-16">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-2xl mx-auto text-center"
      >
        <h1 className="text-5xl font-black mb-6 bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
          Generate AI Memes
        </h1>
        <p className="text-xl text-gray-600 mb-8">Enter any topic and let AI create hilarious memes for you!</p>

        <div className="bg-white/70 backdrop-blur-sm rounded-2xl p-8 shadow-xl border border-purple-200">
          <div className="space-y-6">
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="Enter meme topic (e.g., 'cats', 'programming', 'coffee')"
              className="w-full px-6 py-4 text-lg rounded-xl border-2 border-purple-200 focus:border-purple-500 focus:outline-none transition-colors"
              onKeyPress={(e) => e.key === "Enter" && generateMeme()}
            />

            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={generateMeme}
              disabled={isLoading || !topic.trim()}
              className="w-full bg-gradient-to-r from-purple-500 to-pink-500 text-white font-bold py-4 px-8 rounded-xl hover:from-purple-600 hover:to-pink-600 transition-all shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <div className="flex items-center justify-center">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-white mr-3"></div>
                  Generating Meme...
                </div>
              ) : (
                "🎨 Generate Meme"
              )}
            </motion.button>
          </div>

          {error && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="mt-6 p-4 bg-red-100 border border-red-300 rounded-xl text-red-700"
            >
              {error}
            </motion.div>
          )}

          {generatedMeme && (
            <motion.div initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} className="mt-8">
              <div className="bg-white rounded-2xl p-4 shadow-lg">
                <div className="relative aspect-square max-w-md mx-auto">
                  <Image
                    src={generatedMeme || "/placeholder.svg"}
                    alt={`Generated meme about ${topic}`}
                    fill
                    className="object-cover rounded-xl"
                  />
                </div>
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={downloadMeme}
                  className="w-full mt-4 bg-gradient-to-r from-green-500 to-blue-500 text-white font-semibold py-3 px-6 rounded-xl hover:from-green-600 hover:to-blue-600 transition-all shadow-lg"
                >
                  📥 Download Meme
                </motion.button>
              </div>
            </motion.div>
          )}
        </div>
      </motion.div>
    </div>
  )
}
