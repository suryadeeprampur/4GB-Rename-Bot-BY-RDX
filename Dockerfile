# Use a stable, small base
FROM python:3.11-slim

# Avoid buffering so logs appear in the platform console immediately
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# system deps (ffmpeg needed for some media ops)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      git \
      ffmpeg \
      build-essential \
      && rm -rf /var/lib/apt/lists/*

# copy requirements and install before copying the whole repo (better caching)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# copy project
COPY . /app

# expose health port so it's visible/clear in container metadata
EXPOSE 8080

# default command (adjust if your main file is named differently)
CMD ["python3", "bot.py"]
