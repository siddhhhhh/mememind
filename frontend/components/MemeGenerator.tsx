"use client"

import { useState } from "react"
import { motion } from "framer-motion"
import { Button } from "@/components/ui/button"

export default function MemeGenerator() {
  const [topic, setTopic] = useState("")
  const [generatedMeme, setGeneratedMeme] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const generateMeme = async () => {
    if (!topic.trim()) return

    setIsLoading(true)
    try {
      const response = await fetch("http://127.0.0.1:5000/generate_meme", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ topic: topic.trim() }),
      })

      if (response.ok) {
        const blob = await response.blob()
        const imageUrl = URL.createObjectURL(blob)
        setGeneratedMeme(imageUrl)
      } else {
        console.error("Failed to generate meme")
      }
    } catch (error) {
      console.error("Error generating meme:", error)
    } finally {
      setIsLoading(false)
    }
  }

  const downloadMeme = () => {
    if (!generatedMeme) return

    const link = document.createElement("a")
    link.href = generatedMeme
    link.download = `meme-${Date.now()}.jpg`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="max-w-2xl mx-auto">
      <div className="bg-white rounded-2xl shadow-lg p-8 border-4 border-pink-200">
        <motion.h2
          initial={{ scale: 0.9 }}
          animate={{ scale: 1 }}
          className="text-4xl font-black text-center mb-8 text-gray-800"
        >
          Generate Epic Memes! 🎨
        </motion.h2>

        <div className="space-y-6">
          <div>
            <label className="block text-lg font-bold text-gray-700 mb-2">What's your meme topic? 💭</label>
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="Enter something funny..."
              className="w-full px-4 py-3 border-2 border-gray-300 rounded-2xl focus:border-yellow-300 focus:outline-none text-lg"
              onKeyPress={(e) => e.key === "Enter" && generateMeme()}
            />
          </div>

          <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
            <Button
              onClick={generateMeme}
              disabled={!topic.trim() || isLoading}
              className="w-full py-4 text-xl font-black bg-gradient-to-r from-yellow-300 to-pink-300 hover:from-yellow-400 hover:to-pink-400 text-gray-800 rounded-2xl shadow-lg disabled:opacity-50"
            >
              {isLoading ? (
                <div className="flex items-center justify-center space-x-2">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-gray-800"></div>
                  <span>Cooking meme magic... 🧙‍♂️</span>
                </div>
              ) : (
                "Generate Meme 🚀"
              )}
            </Button>
          </motion.div>
        </div>

        {generatedMeme && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            className="mt-8 text-center"
          >
            <div className="bg-gray-100 rounded-2xl p-4 shadow-inner">
              <img
                src={generatedMeme || "/placeholder.svg"}
                alt="Generated meme"
                className="w-full max-w-md mx-auto rounded-2xl shadow-lg object-cover"
              />
            </div>

            <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
              <Button
                onClick={downloadMeme}
                className="mt-4 px-8 py-3 bg-green-400 hover:bg-green-500 text-gray-800 font-bold rounded-2xl shadow-lg"
              >
                Download Meme 📥
              </Button>
            </motion.div>
          </motion.div>
        )}
      </div>
    </motion.div>
  )
}
