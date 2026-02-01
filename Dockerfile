FROM python:3.11-slim

WORKDIR app

# Install dependencies
RUN pip install --no-cache-dir flask yt-dlp

# Copy the application
COPY app.py .

# Expose port
EXPOSE 8000

# Run the app

CMD [python, app.py]
