# Use Python as base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install FFmpeg and other dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    libffi-dev \
    python3-dev \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create recordings directory
RUN mkdir -p recordings

# Default command
CMD ["python", "main.py"]
