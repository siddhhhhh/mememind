🤖 MemeMind – AI Meme Generator

MemeMind is a Flask + Next.js + TailwindCSS web app that turns any idea into a meme using Google’s Gemini API.
It comes with:
AI-powered meme captions.
Meme generation with preloaded templates.
A gallery of the latest AI-generated memes.
A collection of original meme templates.
Inspired by supermeme.ai, but fully open-source and customizable.
🚀 Features
AI Meme Generator: Enter a topic → AI writes captions → meme is generated.
Latest Memes Page: View and download the most recent 15 generated memes.
OG Templates Page: Browse original meme templates available in static/og_memes.
Modern UI: Built with Next.js App Router + TailwindCSS + Framer Motion animations.
Backend: Flask API with Pillow (PIL) for image manipulation.

⚙️ Setup Instructions
1️⃣ Backend (Flask)

Navigate into backend/:
cd backend

Create a virtual environment and install dependencies:
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
pip install -r requirements.txt

Create a .env file in backend/:
GEMINI_API_KEY=your_google_gemini_api_key_here

Run Flask server:
python app.py

👉 Flask will run at http://127.0.0.1:5000

2️⃣ Frontend (Next.js + Tailwind)
Navigate into frontend/:
cd frontend

Install dependencies:
npm install

Start the development server:
npm run dev

👉 Next.js will run at http://127.0.0.1:3000

3️⃣ Connecting Frontend & Backend
API calls in the frontend use lib/config.ts:
export const API_BASE = "http://127.0.0.1:5000";
Make sure Flask is running on port 5000 while Next.js runs on 3000.

🌟 Pages Overview
Home (/)
Enter a topic → Generate meme → Preview → Download option below.
Latest Memes (/latest)
Displays the 15 most recent memes from static/latest_memes.
OG Templates (/templates)
Displays all original meme formats from static/og_memes.

🖼️ Example Workflow
Open the Home page → enter topic: "AI coding struggles"

Backend:
Picks a random template.
Generates a caption using Gemini.
Creates a meme with PIL.
Saves it to static/latest_memes/.
Meme is returned → displayed in UI → can be downloaded.
It also appears automatically in the Latest Memes page.

🔑 Environment Variables

.env (backend):
GEMINI_API_KEY=your_google_gemini_api_key_here

🛠️ Tech Stack
Backend: Flask, Pillow, Google Gemini API, python-dotenv
Frontend: Next.js (App Router), TailwindCSS, Framer Motion
Other: CORS enabled for API requests

📝 Notes

Free Gemini API limits (AI Studio free tier):
1.5 Flash → 1,500 requests/day
1.5 Pro → 50 requests/day
2.5 Pro (experimental) → ~25 requests/day (as of 2025)

In development, React/Next.js may double API calls because of Strict Mode.
This disappears in production builds.



📜 License
MIT License – free to use and modify.

❤️ Credits
AI captions powered by Google Gemini API.
Meme templates from static/meme_templates and static/og_memes.
UI inspired by supermeme.ai.
Built with Flask + Next.js + TailwindCSS.
