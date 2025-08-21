"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"

const LatestMemes = () => {
  const [memes, setMemes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    fetchLatestMemes()
  }, [])

  const fetchLatestMemes = async () => {
    try {
      const response = await fetch("http://127.0.0.1:5000/get_latest_memes")
      if (!response.ok) {
        throw new Error("Failed to fetch memes")
      }
      const data = await response.json()
      setMemes(data)
    } catch (err) {
      setError("⚠️ Failed to load latest memes")
      console.error("Error fetching memes:", err)
    } finally {
      setLoading(false)
    }
  }

  const downloadMeme = (memeUrl, index) => {
    const link = document.createElement("a")
    link.href = memeUrl
    link.download = `latest-meme-${index + 1}.jpg`
    link.click()
  }

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-16 text-center">
        <div className="text-white text-xl">Loading latest memes... 🔄</div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-16">
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
        className="text-center mb-12"
      >
        <h1 className="text-4xl md:text-6xl font-bold text-white mb-4">Latest Memes 🔥</h1>
        <p className="text-xl text-white/80">Check out the freshest AI-generated memes</p>
      </motion.div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-xl mb-8 max-w-2xl mx-auto">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        {memes.map((memeUrl, index) => (
          <motion.div
            key={index}
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: index * 0.1 }}
            whileHover={{ scale: 1.05 }}
            className="bg-white/70 backdrop-blur-lg rounded-2xl p-4 shadow-2xl hover:shadow-3xl transition-all"
          >
            <img
              src={memeUrl || "/placeholder.svg"}
              alt={`Latest Meme ${index + 1}`}
              className="w-full rounded-xl shadow-lg mb-4"
            />
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => downloadMeme(memeUrl, index)}
              className="w-full bg-gradient-to-r from-green-500 to-blue-500 text-white py-3 rounded-xl font-semibold shadow-lg hover:shadow-xl transition-shadow"
            >
              Download Meme 📥
            </motion.button>
          </motion.div>
        ))}
      </div>

      {memes.length === 0 && !loading && !error && (
        <div className="text-center text-white text-xl">No memes found. Generate some first! 😊</div>
      )}
    </div>
  )
}

export default LatestMemes
