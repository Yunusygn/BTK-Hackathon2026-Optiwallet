# ============================================================
# OptiWallet Frontend — Multi-stage Dockerfile
# ============================================================
# Next.js 14 + TypeScript + PWA
# ============================================================

# ----- Stage 1: Dependencies -----
FROM node:20-alpine AS deps

# libc6-compat for some Node modules
RUN apk add --no-cache libc6-compat

WORKDIR /app

# Dependencies kopyala ve kur (cache layer)
# package-lock.json varsa: npm ci (hızlı, deterministik)
# yoksa: npm install (lock file'ı üretir)
COPY package.json package-lock.json* ./
RUN if [ -f package-lock.json ]; then \
        echo "📦 package-lock.json bulundu — npm ci kullanılıyor"; \
        npm ci --legacy-peer-deps; \
    else \
        echo "📦 package-lock.json yok — npm install kullanılıyor"; \
        npm install --legacy-peer-deps; \
    fi

# ----- Stage 2: Builder -----
FROM node:20-alpine AS builder

WORKDIR /app

# Dependencies'i kopyala
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build için environment
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production

# Production build
RUN npm run build

# ----- Stage 3: Runtime (Development) -----
FROM node:20-alpine AS development

WORKDIR /app

# Development için gereksinimler
RUN apk add --no-cache libc6-compat

# Dependencies'i kopyala
COPY --from=deps /app/node_modules ./node_modules
COPY . .

ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=development
ENV PORT=3000

EXPOSE 3000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000 || exit 1

# Development server (hot reload destekli)
CMD ["npm", "run", "dev"]

# ----- Stage 4: Runtime (Production) -----
FROM node:20-alpine AS production

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000

# Non-root user oluştur
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Production build'i kopyala
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000 || exit 1

CMD ["node", "server.js"]