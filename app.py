"""
Workproof Downloader — one app that serves the UI and the yt-dlp API.

Flow:
  1. GET  /api/info?url=...          -> title, thumbnail, available qualities
  2. POST /api/jobs {url, quality}   -> starts a background download, returns job id
  3. GET  /api/jobs/<id>             -> progress (0-100) and status
  4. GET  /api/jobs/<id>/file        -> the finished file (browser saves it natively)

Files are downloaded on the server (so YouTube/TikTok links that are locked to the
server's IP still work, and video+audio get merged with ffmpeg), then deleted
automatically after FILE_TTL seconds.
"""

import os
import re
import shutil
import tempfile
import threading
import time
import uuid
from html import unescape
from urllib.parse import parse_qs, urljoin, urlparse

import requests
import yt_dlp
from yt_dlp.extractor import gen_extractor_classes
from flask import Flask, abort, jsonify, request, send_file, send_from_directory

# ---------------------------------------------------------------- settings
MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT", "3"))       # downloads at once
MAX_FILESIZE = int(os.getenv("MAX_FILESIZE_MB", "700")) * 1024 * 1024
MAX_DURATION = int(os.getenv("MAX_DURATION_MIN", "120")) * 60
FILE_TTL = int(os.getenv("FILE_TTL_MIN", "20")) * 60          # keep files this long
WORK_DIR = os.getenv("WORK_DIR", os.path.join(tempfile.gettempdir(), "downloader"))
COOKIES_FILE = os.getenv("COOKIES_FILE", "")                  # optional Netscape cookies.txt
VERSION = "2026-11-21.4"                                     # shown in /api/health
QUALITIES = [2160, 1440, 1080, 720, 480, 360, 240]

os.makedirs(WORK_DIR, exist_ok=True)
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app = Flask(__name__, static_folder=None)

jobs = {}                      # job_id -> dict (single gunicorn worker, so in-memory is fine)
jobs_lock = threading.Lock()
slots = threading.BoundedSemaphore(MAX_CONCURRENT)


# ---------------------------------------------------------------- helpers
def base_opts():
    return {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        # Never use the "generic" extractor: it would let anyone make the server
        # fetch arbitrary URLs (including services on the VPS itself).
        "allowed_extractors": ["default", "-generic"],
        "socket_timeout": 20,
    } | ({"cookiefile": COOKIES_FILE} if COOKIES_FILE and os.path.exists(COOKIES_FILE) else {})


# Short links that phones share ("facebook.com/share/v/…", "fb.watch/…", "pin.it/…")
# only redirect to the real post. We follow those redirects ourselves, and only
# while every hop stays on one of these domains, so the server can't be pointed
# at arbitrary or internal addresses.
SOCIAL_DOMAINS = (
    "facebook.com", "fb.watch", "fb.com", "instagram.com", "tiktok.com", "youtube.com",
    "youtu.be", "x.com", "twitter.com", "t.co", "reddit.com", "redd.it", "pinterest.com",
    "pin.it", "threads.net", "threads.com", "snapchat.com", "linkedin.com", "lnkd.in",
    "vimeo.com", "dailymotion.com", "dai.ly", "twitch.tv", "soundcloud.com",
)
EXTRACTORS = [ie for ie in gen_extractor_classes() if ie.IE_NAME != "generic"]
MOBILE_UA = ("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/130.0 Mobile Safari/537.36")


def is_social(url):
    host = (urlparse(url).hostname or "").lower()
    return urlparse(url).scheme in ("http", "https") and any(
        host == d or host.endswith("." + d) for d in SOCIAL_DOMAINS)


SHORT_LINK = re.compile(
    r"^https?://(www\.)?(pin\.it|fb\.watch|t\.co|lnkd\.in|redd\.it|dai\.ly)/"
    r"|/share/|/url_shortener/|reddit\.com/r/[^/]+/s/", re.I)


def has_extractor(url):
    return any(ie.suitable(url) for ie in EXTRACTORS)


def ua_for(url):
    host = urlparse(url).hostname or ""
    # Facebook/Instagram give their link-preview bot the real post address
    # without asking it to log in.
    if any(d in host for d in ("facebook.com", "fb.watch", "fb.com", "instagram.com")):
        return "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)"
    return MOBILE_UA


def url_from_page(base, html):
    """When a share link answers with a page instead of a redirect, the real
    address is usually in og:url, the canonical link or a meta refresh."""
    patterns = (
        r'<meta[^>]+property=["\']og:url["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:url',
        r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)',
        r'<meta[^>]+http-equiv=["\']refresh["\'][^>]+url=([^"\'>]+)',
    )
    for pat in patterns:
        m = re.search(pat, html, re.I)
        if m:
            return urljoin(base, unescape(m.group(1)).strip())
    return None


def next_hop(url):
    """One step: a redirect target, a login page's ?next=, or the page's own URL tag."""
    try:
        resp = requests.get(url, headers={"User-Agent": ua_for(url), "Accept-Language": "en"},
                            timeout=10, allow_redirects=False, stream=True)
    except requests.RequestException:
        return None
    try:
        if resp.status_code in (301, 302, 303, 307, 308) and resp.headers.get("Location"):
            nxt = urljoin(url, resp.headers["Location"])
        elif resp.status_code == 200 and "html" in resp.headers.get("Content-Type", ""):
            html = resp.raw.read(1_000_000, decode_content=True).decode("utf-8", "ignore")
            nxt = url_from_page(url, html)
        else:
            return None
    finally:
        resp.close()
    if not nxt:
        return None
    # redirected to a login wall: the real post is in ?next=
    query = parse_qs(urlparse(nxt).query)
    if "/login" in urlparse(nxt).path and query.get("next"):
        nxt = query["next"][0]
    return nxt if nxt != url else None


def resolve_url(url):
    """Follow share/short links (max 5 hops, social domains only) until we
    reach a URL that a real yt-dlp extractor understands."""
    for _ in range(5):
        if not is_social(url) or (has_extractor(url) and not SHORT_LINK.search(url)):
            return url
        nxt = next_hop(url)
        if not nxt or not is_social(nxt):
            app.logger.warning("could not resolve %s (stopped at %s)", url, nxt)
            return url
        url = nxt
    return url


def clean_url(raw):
    """Accept text like 'Look at this! https://vm.tiktok.com/xyz' and return the URL."""
    if not raw:
        return None
    match = re.search(r"https?://\S+", raw)
    if not match:
        return None
    url = match.group(0).rstrip(".,;)!\"'")
    host = urlparse(url).hostname or ""
    if not host or host in ("localhost",) or host.replace(".", "").isdigit():
        return None
    return resolve_url(url)


def error_code(err):
    """Short code the UI translates (English/Arabic). Match whole phrases only:
    a bare word like "age" also matches "page" and "message"."""
    low = str(err).lower()
    rules = [
        ("unsupported", ("unsupported url", "no suitable extractor")),
        ("bot_check", ("not a bot", "confirm you're not a bot", "confirm you’re not a bot")),
        ("login", ("private video", "this video is private", "login required", "log in to",
                   "sign in to confirm your age", "age-restricted", "requires authentication",
                   "use --cookies", "account is private")),
        ("gone", ("video unavailable", "has been removed", "no longer available",
                  "does not exist", "http error 404")),
        ("blocked", ("http error 403", "http error 429", "blocked", "ip address")),
        ("too_big", ("larger than max filesize", "max-filesize")),
        ("too_long", ("does not pass filter",)),
        ("no_video", ("no video formats", "no video could be found", "requested format is not available")),
    ]
    for code, phrases in rules:
        if any(p in low for p in phrases):
            return code
    return "failed"


def error_detail(err):
    """The raw yt-dlp message (no colours), so failures can be diagnosed."""
    return re.sub(r"\x1b\[[0-9;]*m", "", str(err)).replace("ERROR: ", "")[:300]


def platform_name(info):
    key = (info.get("extractor_key") or info.get("extractor") or "").lower()
    names = {
        "youtube": "YouTube", "tiktok": "TikTok", "instagram": "Instagram",
        "twitter": "X", "facebook": "Facebook", "reddit": "Reddit",
        "vimeo": "Vimeo", "dailymotion": "Dailymotion", "soundcloud": "SoundCloud",
        "twitch": "Twitch", "pinterest": "Pinterest", "snapchat": "Snapchat",
        "threads": "Threads", "linkedin": "LinkedIn",
    }
    for k, v in names.items():
        if key.startswith(k):
            return v
    return info.get("extractor_key") or "Video"


def available_heights(info):
    """Qualities like 1080p/720p, measured on the short side so vertical
    TikTok/Reels videos (1080x1920) show as 1080p, not 1920p."""
    sides = set()
    for f in info.get("formats") or [info]:
        if f.get("vcodec") in (None, "none") and f is not info:
            continue
        w, h = f.get("width"), f.get("height")
        side = min(w, h) if w and h else h
        if side:
            sides.add(side)
    buckets = {min(QUALITIES, key=lambda q: abs(q - side)) for side in sides}
    return sorted(buckets, reverse=True)[:5]


def safe_filename(title, ext):
    title = re.sub(r'[\\/:*?"<>|\n\r\t]+', " ", title or "video").strip()
    title = re.sub(r"\s+", " ", title)[:80] or "video"
    return f"{title}.{ext}"


# ---------------------------------------------------------------- API
@app.get("/api/health")
def health():
    return jsonify(ok=True, version=VERSION, yt_dlp=yt_dlp.version.__version__)


@app.get("/api/info")
def info():
    url = clean_url(request.args.get("url"))
    if not url:
        return jsonify(error="bad_url"), 400
    if SHORT_LINK.search(url) and not has_extractor(url):
        return jsonify(error="short_link", detail=f"could not resolve {url}"), 422
    try:
        with yt_dlp.YoutubeDL(base_opts()) as ydl:
            data = ydl.extract_info(url, download=False)
    except Exception as e:  # noqa: BLE001
        app.logger.warning("info failed for %s: %s", url, e)
        return jsonify(error=error_code(e), detail=error_detail(e)), 422

    if data.get("_type") == "playlist":
        entries = [e for e in (data.get("entries") or []) if e]
        if not entries:
            return jsonify(error="no_video"), 422
        data = entries[0]

    description = data.get("description") or ""
    return jsonify(
        url=url,
        title=data.get("title") or "Untitled video",
        uploader=data.get("uploader") or data.get("channel") or "",
        thumbnail=data.get("thumbnail") or "",
        duration=data.get("duration"),
        platform=platform_name(data),
        description=description[:200],
        qualities=available_heights(data),
    )


def run_job(job_id):
    job = jobs[job_id]
    folder = os.path.join(WORK_DIR, job_id)
    os.makedirs(folder, exist_ok=True)

    def hook(d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes") or 0
            if total:
                # video + audio are two downloads; keep the bar moving forward only
                pct = min(99, int(done * 100 / total))
                job["progress"] = max(job["progress"], pct) if job["part"] == 0 else max(job["progress"], 50 + pct // 2)
        elif d["status"] == "finished":
            job["part"] += 1

    quality = job["quality"]
    opts = base_opts() | {
        "outtmpl": os.path.join(folder, "media.%(ext)s"),
        "progress_hooks": [hook],
        "max_filesize": MAX_FILESIZE,
        "match_filter": yt_dlp.utils.match_filter_func(f"duration <=? {MAX_DURATION}"),
    }
    if quality == "audio":
        opts |= {
            "format": "bestaudio/best",
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}],
        }
    else:
        h = int(quality)
        opts |= {
            # best stream up to this resolution (res = short side, so vertical
            # videos work too); prefer mp4/m4a so it plays on phones and WhatsApp
            "format": "bv*+ba/b",
            "format_sort": [f"res:{h}", "ext:mp4:m4a"],
            "merge_output_format": "mp4",
        }

    job["status"] = "queued"
    with slots:
        job["status"] = "downloading"
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                data = ydl.extract_info(job["url"], download=True)
            files = [f for f in os.listdir(folder) if not f.endswith((".part", ".ytdl"))]
            if not files:
                raise RuntimeError("larger than max filesize or duration filter")
            path = os.path.join(folder, max(files, key=lambda f: os.path.getsize(os.path.join(folder, f))))
            ext = path.rsplit(".", 1)[-1]
            job.update(status="done", progress=100, path=path,
                       filename=safe_filename(data.get("title"), ext),
                       size=os.path.getsize(path))
        except Exception as e:  # noqa: BLE001
            app.logger.warning("job %s failed: %s", job_id, e)
            job.update(status="error", error=error_code(e), detail=error_detail(e))
            shutil.rmtree(folder, ignore_errors=True)


@app.post("/api/jobs")
def create_job():
    body = request.get_json(silent=True) or {}
    url = clean_url(body.get("url"))
    quality = str(body.get("quality", "720"))
    if not url:
        return jsonify(error="bad_url"), 400
    if quality != "audio" and not (quality.isdigit() and int(quality) in QUALITIES):
        return jsonify(error="bad_quality"), 400

    with jobs_lock:
        active = sum(1 for j in jobs.values() if j["status"] in ("queued", "downloading"))
        if active >= MAX_CONCURRENT * 3:
            return jsonify(error="busy"), 429
        job_id = uuid.uuid4().hex
        jobs[job_id] = {"url": url, "quality": quality, "status": "queued", "progress": 0,
                        "part": 0, "created": time.time()}
    threading.Thread(target=run_job, args=(job_id,), daemon=True).start()
    return jsonify(id=job_id), 202


@app.get("/api/jobs/<job_id>")
def job_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify(error="expired"), 404
    return jsonify({k: job.get(k) for k in ("status", "progress", "error", "detail", "filename", "size")})


@app.get("/api/jobs/<job_id>/file")
def job_file(job_id):
    job = jobs.get(job_id)
    if not job or job.get("status") != "done" or not os.path.exists(job.get("path", "")):
        abort(404)
    return send_file(job["path"], as_attachment=True, download_name=job["filename"])


def janitor():
    """Delete finished files after FILE_TTL so the VPS disk never fills up."""
    while True:
        time.sleep(60)
        now = time.time()
        with jobs_lock:
            expired = [k for k, j in jobs.items()
                       if now - j["created"] > FILE_TTL and j["status"] not in ("queued", "downloading")]
            for k in expired:
                jobs.pop(k, None)
        for k in expired:
            shutil.rmtree(os.path.join(WORK_DIR, k), ignore_errors=True)
        # leftovers from a previous container run
        for name in os.listdir(WORK_DIR):
            p = os.path.join(WORK_DIR, name)
            if name not in jobs and now - os.path.getmtime(p) > FILE_TTL:
                shutil.rmtree(p, ignore_errors=True)


threading.Thread(target=janitor, daemon=True).start()


# ---------------------------------------------------------------- UI (static)
@app.get("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.get("/sw.js")
def service_worker():
    # must be served from the root so it controls the whole app
    resp = send_from_directory(STATIC_DIR, "sw.js")
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.get("/<path:name>")
def static_files(name):
    return send_from_directory(STATIC_DIR, name)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")), debug=False)
