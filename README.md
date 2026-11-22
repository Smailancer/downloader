# Downloader

Save videos from TikTok, Instagram, YouTube, X, Facebook, Reddit and ~1,700 other sites.
One app: a Flask API around [yt-dlp](https://github.com/yt-dlp/yt-dlp) that also serves the UI,
installable on Android as a PWA that appears in the **Share** menu of other apps.

## How it works

```
phone share sheet ──► /?text=https://…  (UI reads the link)
UI ──► GET  /api/info?url=…           title, thumbnail, qualities
UI ──► POST /api/jobs {url, quality}   server downloads + merges with ffmpeg
UI ──► GET  /api/jobs/<id>             progress, polled every second
UI ──► GET  /api/jobs/<id>/file        browser saves the file
```

Files are downloaded on the server because many sites (YouTube, TikTok) give links that only
work from the IP that requested them, and because 720p+ on YouTube comes as separate video and
audio streams that need merging. Files are deleted after `FILE_TTL_MIN`.

## Run locally

```bash
pip install -r requirements.txt   # needs ffmpeg installed too
python app.py                     # http://localhost:8000
```

## Deploy on Coolify

Build pack: **Dockerfile**, port **8000**, domain `https://downloader.workproof.one`.

Optional environment variables:

| Variable | Default | Meaning |
|---|---|---|
| `MAX_CONCURRENT` | 3 | downloads running at the same time |
| `MAX_FILESIZE_MB` | 700 | refuse bigger files |
| `MAX_DURATION_MIN` | 120 | refuse longer videos |
| `FILE_TTL_MIN` | 20 | delete finished files after this |
| `UMAMI_WEBSITE_ID` | (none) | Umami website ID; turns analytics on |
| `UMAMI_SRC` | `https://stats.awale.net/script.js` | Umami script URL |
| `COOKIES_FILE` | (none) | path to a cookies.txt (Netscape format) for sites that ask for a login |

**Redeploy every week or two**: the build installs the latest yt-dlp, and sites change their
players often. When a site suddenly stops working, a redeploy usually fixes it.

## Install on a phone

Android (Chrome): open the site → menu → **Install app**. After that, "Downloader" shows up when
you tap **Share** in TikTok, Instagram, X, YouTube…
iPhone: Safari → Share → **Add to Home Screen**. iOS does not let web apps appear in the share
menu, so copy the link and tap **Paste** instead.

## Security notes

- yt-dlp's `generic` extractor is disabled, so the server can't be used to fetch arbitrary URLs
  (including services running on the VPS itself).
- Only one gunicorn worker: jobs live in memory. Scale with threads, not workers.
