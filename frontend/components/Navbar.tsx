"use client"

import { motion } from "framer-motion"
import Link from "next/link"
import { usePathname } from "next/navigation"

export default function Navbar() {
  const pathname = usePathname()

  const navItems = [
    { href: "/", label: "Home", icon: "🏠" },
    { href: "/latest", label: "Latest Memes", icon: "🔥" },
    { href: "/templates", label: "OG Templates", icon: "📸" },
  ]

  return (
    <motion.nav
      initial={{ y: -50, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      className="sticky top-0 z-50 bg-white/80 backdrop-blur-md shadow-lg border-b border-purple-200"
    >
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <Link href="/">
            <motion.h1
              whileHover={{ scale: 1.05 }}
              className="text-3xl font-black bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent cursor-pointer"
            >
              🤖 MemeMind
            </motion.h1>
          </Link>

          <div className="flex space-x-2">
            {navItems.map((item) => (
              <Link key={item.href} href={item.href}>
                <motion.div
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className={`px-4 py-2 rounded-2xl font-semibold transition-all ${
                    pathname === item.href
                      ? "bg-gradient-to-r from-purple-500 to-pink-500 text-white shadow-lg"
                      : "bg-white/50 text-gray-700 hover:bg-gradient-to-r hover:from-purple-100 hover:to-pink-100"
                  }`}
                >
                  <span className="mr-2">{item.icon}</span>
                  {item.label}
                </motion.div>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </motion.nav>
  )
}
