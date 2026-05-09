"use client"

import { motion } from "framer-motion"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { Sparkles, Flame, Layers } from "lucide-react"

const items = [
  { href: "/", label: "Generate", icon: Sparkles },
  { href: "/latest", label: "Latest", icon: Flame },
  { href: "/templates", label: "Templates", icon: Layers },
]

export default function Navbar() {
  const pathname = usePathname()

  return (
    <motion.nav
      initial={{ y: -24, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ type: "spring", stiffness: 220, damping: 24 }}
      className="sticky top-0 z-50"
    >
      <div className="glass-strong">
        <div className="container mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
          <Link href="/" className="group inline-flex items-center gap-2">
            <motion.div
              whileHover={{ rotate: 12, scale: 1.05 }}
              transition={{ type: "spring", stiffness: 300, damping: 12 }}
              className="w-9 h-9 rounded-2xl bg-gradient-to-br from-fuchsia-500 via-pink-500 to-amber-400 grid place-items-center shadow-lg ring-1 ring-white/20"
            >
              <span className="text-lg font-black">M</span>
            </motion.div>
            <span className="text-xl font-black tracking-tight">
              <span className="text-aurora">MemeMind</span>
            </span>
          </Link>

          <div className="flex items-center gap-1 sm:gap-2">
            {items.map(({ href, label, icon: Icon }) => {
              const active = pathname === href
              return (
                <Link key={href} href={href} className="relative">
                  <motion.div
                    whileHover={{ y: -1 }}
                    whileTap={{ scale: 0.96 }}
                    className={`px-3 sm:px-4 py-2 rounded-2xl text-sm font-semibold inline-flex items-center gap-2 transition-colors ${
                      active
                        ? "text-white"
                        : "text-white/65 hover:text-white"
                    }`}
                  >
                    {active && (
                      <motion.span
                        layoutId="nav-pill"
                        className="absolute inset-0 rounded-2xl bg-white/10 ring-1 ring-white/15"
                        transition={{ type: "spring", stiffness: 380, damping: 30 }}
                      />
                    )}
                    <Icon className="w-4 h-4 relative" />
                    <span className="relative hidden sm:inline">{label}</span>
                  </motion.div>
                </Link>
              )
            })}
          </div>
        </div>
      </div>
    </motion.nav>
  )
}
