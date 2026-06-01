# ─────────────────────────────────────────────────────────────────────────────
# DailyByte News — Backend Dockerfile
# FastAPI (Python 3.11) + Node 20 LTS + FFmpeg + HyperFrames (Playwright/Chromium)
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim-bookworm

# Đặt các biến môi trường cần thiết
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    DEBIAN_FRONTEND=noninteractive

# Cài đặt các system packages cơ bản
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    ffmpeg \
    fontconfig \
    unzip \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Cài đặt Node.js 20 LTS
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Cài đặt Font Be Vietnam Pro để render phụ đề tiếng Việt chuẩn đẹp
RUN mkdir -p /usr/share/fonts/truetype/be-vietnam-pro \
    && curl -L -o /tmp/be-vietnam-pro.zip "https://gwfh.mranv.com/api/fonts/be-vietnam-pro?download=zip&subsets=vietnamese,latin" \
    && unzip /tmp/be-vietnam-pro.zip -d /usr/share/fonts/truetype/be-vietnam-pro \
    && rm /tmp/be-vietnam-pro.zip \
    && fc-cache -f -v

# Thiết lập thư mục làm việc
WORKDIR /app

# Cài đặt Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Tạo sẵn thư mục cache và cài đặt Playwright Chromium kèm dependencies của nó
# Dùng npx playwright install --with-deps để tự động cài đặt các system library cần thiết cho headless Chromium
RUN mkdir -p /ms-playwright \
    && npx playwright install --with-deps chromium \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Cài đặt hyperframes package globally để cache npx và chạy thử doctor để test môi trường
RUN npm install -g hyperframes@0.6.20 \
    && hyperframes doctor || true

# Copy toàn bộ code backend vào container
COPY . .

# Expose port của FastAPI
EXPOSE 8000

# Khởi động FastAPI backend
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
