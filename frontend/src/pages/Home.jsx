"use client"

import { useState } from "react"
import { motion } from "framer-motion"

const Home = () => {
  const [topic, setTopic] = useState("")
  const [generatedMeme, setGeneratedMeme] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")

  const generateMeme = async () => {
    if (!topic.trim()) {
      setError("⚠️ Please enter a topic for your meme!")
      return
    }

    setIsLoading(true)
    setError("")

    try {
      const response = await fetch("http://127.0.0.1:5000/generate_meme", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ topic: topic.trim() }),
      })

      if (!response.ok) {
        throw new Error("Failed to generate meme")
      }

      const blob = await response.blob()
      const imageUrl = URL.createObjectURL(blob)
      setGeneratedMeme(imageUrl)
    } catch (err) {
      setError("⚠️ Failed to generate meme, try again")
      console.error("Error generating meme:", err)
    } finally {
      setIsLoading(false)
    }
  }

  const downloadMeme = () => {
    if (generatedMeme) {
      const link = document.createElement("a")
      link.href = generatedMeme
      link.download = `meme-${Date.now()}.jpg`
      link.click()
    }
  }

  const generateAnother = () => {
    setGeneratedMeme(null)
    setTopic("")
    setError("")
  }

  return (
    <div className="container mx-auto px-4 py-16">
      <motion.div
        initial={{ opacity: 0, y: 50 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
        className="text-center mb-12"
      >
        <h1 className="text-5xl md:text-7xl font-bold text-white mb-6">MemeMind 🤖</h1>
        <h2 className="text-2xl md:text-3xl font-semibold text-white/90 mb-4">AI Meme Generator</h2>
        <p className="text-xl text-white/80 max-w-2xl mx-auto">Turn any idea into a viral meme in seconds. 🔥😂</p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: 0.2 }}
        className="max-w-2xl mx-auto"
      >
        <div className="bg-white/70 backdrop-blur-lg rounded-2xl p-8 shadow-2xl">
          <div className="space-y-6">
            <div>
              <label className="block text-gray-700 font-semibold mb-3 text-lg">Enter a topic for your meme:</label>
              <input
                type="text"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="e.g., AI coding struggles"
                className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent text-lg"
                onKeyPress={(e) => e.key === "Enter" && generateMeme()}
              />
            </div>

            {error && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-xl"
              >
                {error}
              </motion.div>
            )}

            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={generateMeme}
              disabled={isLoading}
              className="w-full bg-gradient-to-r from-purple-600 to-pink-600 text-white py-4 rounded-xl font-bold text-lg shadow-lg hover:shadow-xl transition-shadow disabled:opacity-50"
            >
              {isLoading ? "Cooking meme magic… 🍳" : "Generate Meme 🎉"}
            </motion.button>
          </div>
        </div>
      </motion.div>

      {generatedMeme && (
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
          className="max-w-2xl mx-auto mt-12"
        >
          <div className="bg-white/70 backdrop-blur-lg rounded-2xl p-6 shadow-2xl">
            <img
              src={generatedMeme || "/placeholder.svg"}
              alt="Generated Meme"
              className="w-full rounded-xl shadow-lg mb-6"
            />
            <div className="flex gap-4 justify-center">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={downloadMeme}
                className="bg-green-500 hover:bg-green-600 text-white px-6 py-3 rounded-xl font-semibold shadow-lg transition-colors"
              >
                Download Meme 📥
              </motion.button>
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={generateAnother}
                className="bg-purple-500 hover:bg-purple-600 text-white px-6 py-3 rounded-xl font-semibold shadow-lg transition-colors"
              >
                Generate Another 🔄
              </motion.button>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  )
}

export default Home
