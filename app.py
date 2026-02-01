from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)

# Enable CORS for your frontend domain
CORS(app, resources={
    r"/info": {
        "origins": ["https://downloader.workproof.one", "http://downloader.workproof.one"],
        "methods": ["GET", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    },
    r"/supported": {
        "origins": ["https://downloader.workproof.one", "http://downloader.workproof.one"],
        "methods": ["GET", "OPTIONS"]
    }
})

# Or allow all origins (less secure but easier for testing):
# CORS(app, origins="*")

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
            "no_warnings": True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            data = ydl.extract_info(url, download=False)
            
        # Extract only useful fields to reduce response size
        result = {
            "title": data.get("title", "Unknown"),
            "description": data.get("description", "")[:200] + "..." if len(data.get("description", "")) > 200 else data.get("description", ""),
            "thumbnail": data.get("thumbnail", ""),
            "duration": data.get("duration"),
            "uploader": data.get("uploader", "Unknown"),
            "formats": [],
            "original_url": data.get("original_url", url)
        }
        
        # Get video formats with both video and audio
        if "formats" in data:
            seen_qualities = set()
            for f in data["formats"]:
                if f.get("vcodec") != "none" and f.get("acodec") != "none":
                    quality = f.get("quality_label") or f"{f.get('height', 'unknown')}p"
                    if quality not in seen_qualities:
                        seen_qualities.add(quality)
                        result["formats"].append({
                            "format_id": f["format_id"],
                            "ext": f["ext"],
                            "quality": quality,
                            "url": f.get("url", "")
                        })
                # Limit to 5 options
                if len(result["formats"]) >= 5:
                    break
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/supported")
def supported_sites():
    sites = [
        {"name": "YouTube", "icon": "▶️", "url": "youtube.com"},
        {"name": "Facebook", "icon": "📘", "url": "facebook.com"},
        {"name": "Twitter/X", "icon": "𝕏", "url": "x.com"},
        {"name": "TikTok", "icon": "🎵", "url": "tiktok.com"},
        {"name": "Instagram", "icon": "📷", "url": "instagram.com"},
        {"name": "Reddit", "icon": "🔴", "url": "reddit.com"},
        {"name": "SoundCloud", "icon": "🎧", "url": "soundcloud.com"},
        {"name": "Twitch", "icon": "🎮", "url": "twitch.tv"},
        {"name": "Vimeo", "icon": "🎬", "url": "vimeo.com"},
        {"name": "Dailymotion", "icon": "📺", "url": "dailymotion.com"}
    ]
    return jsonify(sites)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
