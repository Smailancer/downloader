FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir flask yt-dlp

COPY app.py .

EXPOSE 8000

# Use shell form (simpler, no JSON brackets to mess up)
CMD python app.py
