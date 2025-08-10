# app.py - The core backend for the MemeMind AI Meme Generator

import os
import random
import io
import textwrap
import time
from flask import Flask, request, send_file, jsonify, url_for
from flask_cors import CORS # Import the CORS library
from PIL import Image, ImageDraw, ImageFont
import google.generativeai as genai
from dotenv import load_dotenv

# --- 1. INITIAL SETUP & CONFIGURATION ---

DEVELOPMENT_MODE = False

load_dotenv()
app = Flask(__name__, static_folder='static')

# --- NEW: Enable CORS for all routes ---
# This tells the browser to allow requests from your React app.
CORS(app)

LATEST_MEMES_DIR = os.path.join(app.static_folder, 'latest_memes')
os.makedirs(LATEST_MEMES_DIR, exist_ok=True)


if not DEVELOPMENT_MODE:
    try:
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model = genai.GenerativeModel('gemini-1.5-flash')
        print("Gemini API configured successfully.")
    except Exception as e:
        print(f"Error configuring Gemini API: {e}")
        model = None
else:
    print("--- RUNNING IN DEVELOPMENT MODE ---")
    model = None

MEME_TEMPLATES_DIR = os.path.join(app.static_folder, 'meme_templates')
try:
    FONT_PATH = 'arial.ttf'
    ImageFont.truetype(FONT_PATH, 10)
except IOError:
    FONT_PATH = None

# --- 2. HELPER FUNCTIONS (Unchanged) ---
def get_random_template():
    try:
        templates = [f for f in os.listdir(MEME_TEMPLATES_DIR) if f.endswith(('.png', '.jpg', '.jpeg'))]
        if not templates: return None, None
        random_template_name = random.choice(templates)
        template_path = os.path.join(MEME_TEMPLATES_DIR, random_template_name)
        clean_name = os.path.splitext(random_template_name)[0].replace('_', ' ').title()
        return template_path, clean_name
    except FileNotFoundError:
        return None, None

def generate_caption(topic, template_name):
    if DEVELOPMENT_MODE:
        return f"{topic} | (Generated in Dev Mode)"
    if not model:
        return "API Key Error | Check Server Logs"
    prompt = f"""
    You are an expert AI meme generator. Your task is to create a funny, witty, and culturally relevant caption for a meme.
    **Topic:** "{topic}"
    **Meme Format:** "{template_name}"
    Generate a short, impactful caption. The caption must have two parts, separated by a pipe symbol (|).
    Example Response: Me explaining my code | The one line that actually works
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        if "quota" in str(e).lower():
            return "Daily API Limit Reached | Please try again tomorrow."
        return f"API Error | Could not generate caption"

def create_meme_image(template_path, top_text, bottom_text):
    try:
        template_img = Image.open(template_path).convert("RGB")
        width, height = template_img.size
        padding = 20
        font_size = int(width / 20)
        font = ImageFont.truetype(FONT_PATH, font_size) if FONT_PATH else ImageFont.load_default()
        
        draw = ImageDraw.Draw(template_img)
        max_chars = int(width * 0.9 / (font_size * 0.5))
        wrapped_top = "\n".join(textwrap.wrap(top_text, max_chars))
        wrapped_bottom = "\n".join(textwrap.wrap(bottom_text, max_chars))
        
        top_bbox = draw.textbbox((0,0), wrapped_top, font=font)
        bottom_bbox = draw.textbbox((0,0), wrapped_bottom, font=font)
        text_height = (top_bbox[3] - top_bbox[1]) + (bottom_bbox[3] - bottom_bbox[1]) + (padding * 3)

        final_image = Image.new('RGB', (width, height + text_height), 'white')
        final_image.paste(template_img, (0, 0))
        
        draw = ImageDraw.Draw(final_image)
        top_text_x = (width - (top_bbox[2] - top_bbox[0])) / 2
        top_text_y = height + padding
        draw.text((top_text_x, top_text_y), wrapped_top, font=font, fill="black", align="center")
        
        line_y = top_text_y + (top_bbox[3] - top_bbox[1]) + (padding / 2)
        draw.line([(padding, line_y), (width - padding, line_y)], fill="lightgray", width=1)

        bottom_text_x = (width - (bottom_bbox[2] - bottom_bbox[0])) / 2
        bottom_text_y = line_y + (padding / 2)
        draw.text((bottom_text_x, bottom_text_y), wrapped_bottom, font=font, fill="black", align="center")
        
        return final_image
    except Exception as e:
        print(f"Error creating meme image: {e}")
        return None

# --- 3. API ENDPOINTS ---

@app.route('/generate_meme', methods=['POST'])
def generate_meme_endpoint():
    data = request.get_json()
    topic = data.get('topic')
    if not topic: return jsonify({"error": "Topic not provided"}), 400
    
    template_path, template_name = get_random_template()
    if not template_path: return jsonify({"error": "No meme templates found"}), 500

    caption = generate_caption(topic, template_name)
    top_text, bottom_text = (caption.split('|', 1) + [""])[:2]
    
    final_image = create_meme_image(template_path, top_text.strip(), bottom_text.strip())
    if not final_image: return jsonify({"error": "Failed to create meme image"}), 500

    try:
        filename = f"meme_{int(time.time())}.jpg"
        save_path = os.path.join(LATEST_MEMES_DIR, filename)
        final_image.save(save_path, 'JPEG', quality=85)
    except Exception as e:
        print(f"Error saving meme: {e}")

    img_io = io.BytesIO()
    final_image.save(img_io, 'JPEG', quality=90)
    img_io.seek(0)
    return send_file(img_io, mimetype='image/jpeg')

@app.route('/get_latest_memes')
def get_latest_memes():
    try:
        files = os.listdir(LATEST_MEMES_DIR)
        image_files = [f for f in files if f.endswith(('.jpg', '.png', '.jpeg'))]
        image_files.sort(key=lambda x: os.path.getmtime(os.path.join(LATEST_MEMES_DIR, x)), reverse=True)
        
        # Use _external=False to generate relative URLs
        meme_urls = [url_for('static', filename=f'latest_memes/{fname}', _external=False) for fname in image_files[:15]]
        
        return jsonify(meme_urls)
    except Exception as e:
        print(f"Error getting latest memes: {e}")
        return jsonify({"error": "Could not retrieve latest memes"}), 500
    

# Add this new endpoint to your app.py file
@app.route('/get_og_memes')
def get_og_memes():
    OG_MEMES_DIR = os.path.join(app.static_folder, 'og_memes')
    try:
        # Ensure the directory exists
        if not os.path.isdir(OG_MEMES_DIR):
            return jsonify([])

        files = os.listdir(OG_MEMES_DIR)
        image_files = [f for f in files if f.endswith(('.jpg', '.png', '.jpeg'))]
        # Generate URLs for each image
        meme_urls = [url_for('static', filename=f'og_memes/{fname}', _external=False) for fname in image_files]
        return jsonify(meme_urls)
    except Exception as e:
        print(f"Error getting OG memes: {e}")
        return jsonify({"error": "Could not retrieve OG memes"}), 500


if __name__ == '__main__':
    app.run(debug=True)
