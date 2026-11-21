FROM python:3.11-slim

# ffmpeg merges video + audio (YouTube 720p/1080p) and converts audio to mp3
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# YouTube now needs a JavaScript runtime for yt-dlp to solve its player challenges
COPY --from=denoland/deno:bin /deno /usr/local/bin/deno

WORKDIR /app
COPY requirements.txt .
# --upgrade so every redeploy pulls the newest yt-dlp (sites change often)
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY app.py .
COPY static ./static

ENV PORT=8000 PYTHONUNBUFFERED=1
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/api/health')"

# 1 worker (jobs live in memory) with many threads; long timeout for big files
CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:${PORT} --workers 1 --threads 16 --timeout 600"]
