# ─────────────────────────────────────────────────────────────────────────────
# DailyByte News — Frontend Dockerfile
# Multi-stage Next.js Standalone Build
# ─────────────────────────────────────────────────────────────────────────────

# Stage 1: Cài đặt dependencies
FROM node:20-alpine AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Sao chép file package.json và package-lock.json
COPY package.json package-lock.json ./
RUN npm ci

# Stage 2: Build source code
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Định nghĩa Build Arg cho API URL của backend (Next.js bake biến này lúc build)
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# Tắt telemetry của Next.js lúc build
ENV NEXT_TELEMETRY_DISABLED=1

RUN npm run build

# Stage 3: Production runner
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
# Tắt telemetry của Next.js lúc runtime
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public

# Tận dụng standalone build để giảm thiểu tối đa kích thước container image
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
