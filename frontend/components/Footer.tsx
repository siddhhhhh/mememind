"use client"

import { motion } from "framer-motion"

export default function Footer() {
  const currentYear = new Date().getFullYear()

  return (
    <motion.footer
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="bg-gradient-to-r from-purple-900 to-pink-900 text-white py-8 mt-16"
    >
      <div className="container mx-auto px-4 text-center">
        <p className="text-lg">© {currentYear} MemeMind. Built with ❤️ using Gemini API</p>
      </div>
    </motion.footer>
  )
}
