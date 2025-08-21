"use client"

import { Link, useLocation } from "react-router-dom"
import { motion } from "framer-motion"

const Navbar = () => {
  const location = useLocation()

  const navItems = [
    { path: "/", label: "Home", emoji: "🏠" },
    { path: "/latest", label: "Latest Memes", emoji: "🔥" },
    { path: "/og-templates", label: "OG Templates", emoji: "👑" },
  ]

  return (
    <motion.nav
      initial={{ y: -50, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      className="bg-white/10 backdrop-blur-md border-b border-white/20 sticky top-0 z-50"
    >
      <div className="container mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          <Link to="/">
            <motion.h1 whileHover={{ scale: 1.05 }} className="text-3xl font-black text-white">
              🤖 MemeMind
            </motion.h1>
          </Link>

          <div className="flex items-center space-x-4">
            <div className="flex space-x-2">
              {navItems.map((item) => (
                <Link key={item.path} to={item.path}>
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    className={`px-4 py-2 rounded-xl font-bold transition-all duration-200 ${
                      location.pathname === item.path
                        ? "bg-white text-purple-600 shadow-lg"
                        : "bg-white/20 text-white hover:bg-white/30"
                    }`}
                  >
                    <span className="mr-2">{item.emoji}</span>
                    <span className="hidden sm:inline">{item.label}</span>
                  </motion.button>
                </Link>
              ))}
            </div>

            <Link to="/">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="bg-gradient-to-r from-yellow-400 to-orange-500 text-white px-6 py-2 rounded-xl font-bold shadow-lg hover:shadow-xl transition-shadow"
              >
                Generate Meme
              </motion.button>
            </Link>
          </div>
        </div>
      </div>
    </motion.nav>
  )
}

export default Navbar
