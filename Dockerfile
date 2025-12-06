FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system packages
RUN apt update && apt install -y \
    git \
    ffmpeg \
    python3-pip \
    && apt clean \
    && rm -rf /var/lib/apt/lists/*

# Install requirements first (faster Docker caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose port for web server (important for Koyeb/Render/Railway)
EXPOSE 8080

# Command to start bot
CMD ["python3", "bot.py"]
