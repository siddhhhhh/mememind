import { Routes, Route } from "react-router-dom"
import Navbar from "./components/Navbar"
import Footer from "./components/Footer"
import Home from "./pages/Home"
import LatestMemes from "./pages/LatestMemes"
import OGMemes from "./pages/OGMemes"
import "./index.css"

function App() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-500 to-pink-500">
      <Navbar />
      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/latest" element={<LatestMemes />} />
          <Route path="/og-templates" element={<OGMemes />} />
        </Routes>
      </main>
      <Footer />
    </div>
  )
}

export default App
