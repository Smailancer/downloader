from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import json

app = Flask(__name__)
# Enable CORS for your domain (and localhost for testing)
CORS(app, origins=["http://workproof.one", "https://workproof.one", "http://localhost", "http://127.0.0.1"])

@app.route("/")
def home():
    return "yt-dlp API is running"

@app.route("/info")
def info():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "Missing url parameter"}), 400
    
    try:
        ydl_opts = {
            "quiet": True, 
            "no_warnings": True,
            "extract_flat": False
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            data = ydl.extract_info(url, download=False)
            
        # Extract only useful fields
        result = {
            "title": data.get("title", "Unknown"),
            "description": data.get("description", ""),
            "thumbnail": data.get("thumbnail", ""),
            "duration": data.get("duration"),
            "uploader": data.get("uploader", "Unknown"),
            "formats": [],
            "original_url": data.get("original_url", url)
        }
        
        # Get best quality formats (video + audio)
        if "formats" in data:
            for f in data["formats"]:
                if f.get("vcodec") != "none" and f.get("acodec") != "none":
                    result["formats"].append({
                        "format_id": f["format_id"],
                        "ext": f["ext"],
                        "quality": f.get("quality_label", f.get("height", "unknown")),
                        "url": f.get("url", "")
                    })
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/supported")
def supported_sites():
    """Return list of supported sites"""
    sites = [
        {"name": "YouTube", "url": "youtube.com", "icon": "▶️"},
        {"name": "Facebook", "url": "facebook.com", "icon": "📘"},
        {"name": "Twitter/X", "url": "twitter.com/x.com", "icon": "🐦"},
        {"name": "TikTok", "url": "tiktok.com", "icon": "🎵"},
        {"name": "Instagram", "url": "instagram.com", "icon": "📷"},
        {"name": "Reddit", "url": "reddit.com", "icon": "🔴"},
        {"name": "SoundCloud", "url": "soundcloud.com", "icon": "🎧"},
        {"name": "Twitch", "url": "twitch.tv", "icon": "🎮"},
        {"name": "Vimeo", "url": "vimeo.com", "icon": "🎬"},
        {"name": "Dailymotion", "url": "dailymotion.com", "icon": "📺"}
    ]
    return jsonify(sites)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
