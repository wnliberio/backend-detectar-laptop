# backend-detectar/Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

USER root
RUN mkdir -p /tmp && chmod 1777 /tmp

# System dependencies required by OCR, database drivers and Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    pkg-config \
    libxml2-dev \
    libxslt1-dev \
    libffi-dev \
    unixodbc-dev \
    tesseract-ocr \
    libtesseract-dev \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    libpng-dev \
    libfreetype6-dev \
    libwebp-dev \
    libopenjp2-7 \
    libtiff-dev \
    python3-tk \
    scrot \
    libx11-6 \
    libxext6 \
    libxtst6 \
    libxrender1 \
    libxi6 \
    libxfixes3 \
    xvfb \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# dependencies
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# application code
COPY . .

# expose port
ENV PORT=8000
EXPOSE 8000

# default entry module
ENV APP_MODULE=app.main:app
CMD ["sh","-lc","gunicorn -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 ${APP_MODULE}"]

