FROM node:22-alpine AS frontend
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci
COPY index.html vite.config.js ./
COPY src ./src
COPY public ./public
RUN npm run build

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    APP_DATA_DIR=/data \
    APP_SECURE_COOKIE=1 \
    APP_TRUST_PROXY=1
WORKDIR /app
RUN useradd --system --create-home --uid 10001 app \
    && mkdir -p /data \
    && chown app:app /data
COPY server ./server
COPY scripts ./scripts
COPY public ./public
COPY --from=frontend /build/dist ./dist
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)" || exit 1
CMD ["python", "-m", "server.app"]
