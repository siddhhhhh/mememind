"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { Button } from "@/components/ui/button"

export default function OGMemes() {
  const [templates, setTemplates] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    fetchOGMemes()
  }, [])

  const fetchOGMemes = async () => {
    try {
      const response = await fetch("http://127.0.0.1:5000/get_og_memes")
      if (response.ok) {
        const data = await response.json()
        setTemplates(data)
      }
    } catch (error) {
      console.error("Error fetching OG memes:", error)
    } finally {
      setIsLoading(false)
    }
  }

  const downloadTemplate = (templateUrl: string, index: number) => {
    const link = document.createElement("a")
    link.href = templateUrl
    link.download = `og-template-${index + 1}.jpg`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-pink-400"></div>
        <span className="ml-4 text-xl font-bold">Loading classic templates... 📸</span>
      </div>
    )
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="max-w-6xl mx-auto">
      <motion.h2 initial={{ y: -20 }} animate={{ y: 0 }} className="text-4xl font-black text-center mb-8 text-gray-800">
        OG Meme Templates 📸
      </motion.h2>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {templates.map((templateUrl, index) => (
          <motion.div
            key={index}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            whileHover={{ scale: 1.05 }}
            className="bg-white rounded-2xl shadow-lg overflow-hidden border-2 border-gray-200 hover:border-pink-300 transition-all"
          >
            <div className="aspect-square bg-gray-100">
              <img
                src={templateUrl || "/placeholder.svg"}
                alt={`OG template ${index + 1}`}
                className="w-full h-full object-cover"
                onLoad={(e) => {
                  const target = e.target as HTMLImageElement
                  target.style.opacity = "1"
                }}
                style={{ opacity: 0, transition: "opacity 0.3s" }}
              />
            </div>

            <div className="p-4">
              <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                <Button
                  onClick={() => downloadTemplate(templateUrl, index)}
                  className="w-full bg-yellow-300 hover:bg-yellow-400 text-gray-800 font-bold rounded-2xl"
                >
                  Download Template 📥
                </Button>
              </motion.div>
            </div>
          </motion.div>
        ))}
      </div>

      {templates.length === 0 && (
        <div className="text-center py-12">
          <p className="text-xl text-gray-600">No templates available! 😢</p>
          <p className="text-lg text-gray-500 mt-2">Check back later for classic meme formats! 🎭</p>
        </div>
      )}
    </motion.div>
  )
}
