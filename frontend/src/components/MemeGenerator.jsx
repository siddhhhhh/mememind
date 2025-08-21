"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"

const MemeGenerator = () => {
  const [topic, setTopic] = useState("")
  const [generatedMeme, setGeneratedMeme] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")

  const generateMeme = async (e) => {
    e.preventDefault()
    if (!topic.trim()) return

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
      setError("Failed to generate meme. Make sure the Flask server is running!")
      console.error("Error generating meme:", err)
    } finally {
      setIsLoading(false)
    }
  }

  const downloadMeme = () => {
    if (!generatedMeme) return

    const link = document.createElement("a")
    link.href = generatedMeme
    link.download = `meme-${topic.replace(/\s+/g, "-")}.jpg`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="max-w-2xl mx-auto">
      <div className="bg-white rounded-2xl shadow-lg p-8 mb-8">
        <motion.h2
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-4xl font-black text-center mb-8 text-transparent bg-clip-text bg-gradient-to-r from-purple-600 to-pink-600"
        >
          Generate Epic Memes! 🎨
        </motion.h2>

        <form onSubmit={generateMeme} className="space-y-6">
          <div>
            <label htmlFor="topic" className="block text-lg font-bold text-gray-700 mb-2">
              What's your meme about? 🤔
            </label>
            <input
              type="text"
              id="topic"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="Enter a funny topic... (e.g., 'cats being dramatic')"
              className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-purple-500 focus:outline-none text-lg"
              disabled={isLoading}
            />
          </div>

          <motion.button
            type="submit"
            disabled={isLoading || !topic.trim()}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="w-full bg-gradient-to-r from-purple-500 to-pink-500 text-white font-black text-xl py-4 rounded-xl shadow-lg hover:shadow-xl transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <div className="flex items-center justify-center space-x-2">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-white"></div>
                <span>Cooking meme magic... 🧙‍♂️</span>
              </div>
            ) : (
              "Generate Meme 🚀"
            )}
          </motion.button>
        </form>

        {error && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="mt-4 p-4 bg-red-100 border border-red-300 rounded-xl text-red-700 font-semibold"
          >
            {error}
          </motion.div>
        )}
      </div>

      <AnimatePresence>
        {generatedMeme && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="bg-white rounded-2xl shadow-lg p-6"
          >
            <h3 className="text-2xl font-black text-center mb-4 text-gray-800">Your Fresh Meme! 🔥</h3>

            <div className="relative">
              <img
                src={generatedMeme || "/placeholder.svg"}
                alt="Generated meme"
                className="w-full h-auto rounded-xl shadow-md object-cover"
              />
            </div>

            <motion.button
              onClick={downloadMeme}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="w-full mt-4 bg-yellow-300 hover:bg-yellow-400 text-purple-800 font-black text-lg py-3 rounded-xl shadow-lg transition-all duration-200"
            >
              Download Meme 📥
            </motion.button>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export default MemeGenerator
