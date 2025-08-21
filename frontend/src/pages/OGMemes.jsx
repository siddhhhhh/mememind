"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"

const OGMemes = () => {
  const [templates, setTemplates] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    fetchOGMemes()
  }, [])

  const fetchOGMemes = async () => {
    try {
      const response = await fetch("http://127.0.0.1:5000/get_og_memes")
      if (!response.ok) {
        throw new Error("Failed to fetch templates")
      }
      const data = await response.json()
      setTemplates(data)
    } catch (err) {
      setError("⚠️ Failed to load OG templates")
      console.error("Error fetching templates:", err)
    } finally {
      setLoading(false)
    }
  }

  const downloadTemplate = (templateUrl, index) => {
    const link = document.createElement("a")
    link.href = templateUrl
    link.download = `og-template-${index + 1}.jpg`
    link.click()
  }

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-16 text-center">
        <div className="text-white text-xl">Loading OG templates... 🔄</div>
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
        <h1 className="text-4xl md:text-6xl font-bold text-white mb-4">OG Templates 📜</h1>
        <p className="text-xl text-white/80">Classic meme formats that never go out of style</p>
      </motion.div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-xl mb-8 max-w-2xl mx-auto">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        {templates.map((templateUrl, index) => (
          <motion.div
            key={index}
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: index * 0.1 }}
            whileHover={{ scale: 1.05 }}
            className="bg-white/70 backdrop-blur-lg rounded-2xl p-4 shadow-2xl hover:shadow-3xl transition-all"
          >
            <div className="relative">
              <img
                src={templateUrl || "/placeholder.svg"}
                alt={`OG Template ${index + 1}`}
                className="w-full rounded-xl shadow-lg mb-4"
              />
              <div className="absolute top-2 right-2 bg-purple-500 text-white px-3 py-1 rounded-full text-sm font-semibold">
                Classic Format
              </div>
            </div>
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => downloadTemplate(templateUrl, index)}
              className="w-full bg-gradient-to-r from-purple-500 to-pink-500 text-white py-3 rounded-xl font-semibold shadow-lg hover:shadow-xl transition-shadow"
            >
              Download Template 📥
            </motion.button>
          </motion.div>
        ))}
      </div>

      {templates.length === 0 && !loading && !error && (
        <div className="text-center text-white text-xl">No templates found. 😔</div>
      )}
    </div>
  )
}

export default OGMemes
