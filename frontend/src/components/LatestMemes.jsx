"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"

const LatestMemes = () => {
  const [memes, setMemes] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    fetchLatestMemes()
  }, [])

  const fetchLatestMemes = async () => {
    try {
      const response = await fetch("http://127.0.0.1:5000/get_latest_memes")
      if (!response.ok) {
        throw new Error("Failed to fetch latest memes")
      }
      const data = await response.json()
      setMemes(data)
    } catch (err) {
      setError("Failed to load latest memes. Make sure the Flask server is running!")
      console.error("Error fetching latest memes:", err)
    } finally {
      setIsLoading(false)
    }
  }

  const downloadMeme = (memeUrl, index) => {
    const link = document.createElement("a")
    link.href = memeUrl
    link.download = `latest-meme-${index + 1}.jpg`
    link.target = "_blank"
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500 mx-auto mb-4"></div>
          <p className="text-xl font-bold text-gray-600">Loading fresh memes... 🔄</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="text-center p-8 bg-red-100 rounded-2xl border border-red-300"
      >
        <p className="text-xl font-bold text-red-700">{error}</p>
      </motion.div>
    )
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="max-w-6xl mx-auto">
      <motion.h2
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="text-4xl font-black text-center mb-8 text-transparent bg-clip-text bg-gradient-to-r from-purple-600 to-pink-600"
      >
        Latest Fire Memes 🔥
      </motion.h2>

      {memes.length === 0 ? (
        <div className="text-center p-8 bg-yellow-100 rounded-2xl">
          <p className="text-xl font-bold text-gray-600">No memes yet! Generate some first 🎨</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {memes.map((memeUrl, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              whileHover={{ scale: 1.02 }}
              className="bg-white rounded-2xl shadow-lg overflow-hidden group"
            >
              <div className="relative">
                <img
                  src={memeUrl || "/placeholder.svg"}
                  alt={`Latest meme ${index + 1}`}
                  className="w-full h-64 object-cover transition-transform duration-200 group-hover:scale-105"
                />
                <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-20 transition-all duration-200 flex items-center justify-center">
                  <motion.button
                    onClick={() => downloadMeme(memeUrl, index)}
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.9 }}
                    className="opacity-0 group-hover:opacity-100 bg-yellow-300 hover:bg-yellow-400 text-purple-800 font-black px-4 py-2 rounded-xl shadow-lg transition-all duration-200"
                  >
                    Download 📥
                  </motion.button>
                </div>
              </div>

              <div className="p-4">
                <motion.button
                  onClick={() => downloadMeme(memeUrl, index)}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className="w-full bg-pink-200 hover:bg-pink-300 text-purple-800 font-bold py-2 rounded-xl transition-all duration-200"
                >
                  Download Meme 📥
                </motion.button>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </motion.div>
  )
}

export default LatestMemes
