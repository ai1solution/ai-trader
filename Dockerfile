# Unified Dockerfile for Render Deployment
# Serves both Next.js frontend and FastAPI backend in one container

# Stage 1: Build Backend Dependencies
FROM python:3.11-slim as python-base
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Build Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app

# Copy frontend files
COPY web_mvp_fresh/package.json web_mvp_fresh/package-lock.json* ./
RUN npm ci

COPY web_mvp_fresh .

# Build for production
ENV NEXT_PUBLIC_API_URL=/api
ENV NODE_ENV=production
RUN npm run build

# Stage 3: Final production image
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies (curl for health checks, node for Next.js)
RUN apt-get update && apt-get install -y \
    curl \
    nodejs \
    npm \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from python-base
COPY --from=python-base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=python-base /usr/local/bin /usr/local/bin

# Copy backend code
COPY engine_api ./engine_api
COPY v1_legacy ./v1_legacy
COPY v2_modern ./v2_modern
COPY v3 ./v3
COPY v4 ./v4
COPY common ./common

# Copy built frontend
COPY --from=frontend-builder /app/.next/standalone ./frontend
COPY --from=frontend-builder /app/.next/static ./frontend/.next/static
COPY --from=frontend-builder /app/public ./frontend/public

# Create necessary directories
RUN mkdir -p logs results

# Environment variables (PORT will be set by Render)
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV NODE_ENV=production
ENV PORT=10000

# Copy startup script
COPY start.sh .
RUN chmod +x start.sh

# Expose port (Render dynamically assigns PORT)
EXPOSE ${PORT}

# Health check - must check the PORT that Render assigns
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-10000} || exit 1

# Start both services
CMD ["./start.sh"]
