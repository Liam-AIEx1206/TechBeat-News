# slide-engine — Node + Playwright Chromium (thay Electron BrowserWindow).
# Chạy headless: HTTP adapter :8100, sinh/sửa/xuất slide qua các IPC channel gốc.
FROM node:22-bookworm

WORKDIR /app

# Cài deps trước (tận dụng cache). shim electron/electron-log là file-dep local
# → phải copy trước khi npm ci.
COPY package.json package-lock.json ./
COPY shims ./shims
RUN npm ci --no-audit --no-fund

# Chromium + system deps cho Playwright (khớp version playwright đã cài).
RUN npx playwright install --with-deps chromium

# Mã nguồn + vendor + resources (styles/skills/fonts) + data/templates (bake sẵn).
COPY . .

ENV NODE_ENV=production \
    SLIDE_ENGINE_DATA_DIR=/app/data \
    SLIDE_ENGINE_PORT=8100 \
    SLIDE_ENGINE_MODEL=gpt-5

EXPOSE 8100
CMD ["npx", "tsx", "src/server.ts"]
