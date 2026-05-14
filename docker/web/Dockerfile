# ── Stage 1: compile Tailwind CSS ─────────────────────────────────────────────
FROM node:20-alpine AS css-builder

WORKDIR /app

# Cache npm layer separately from source — only re-runs when package*.json changes
COPY theme/static_src/package*.json ./theme/static_src/
RUN npm --prefix theme/static_src ci --omit=dev

# Copy source needed by tailwind (config + templates for content scanning)
COPY theme/static_src/ ./theme/static_src/
COPY apps/             ./apps/

# Run from the static_src directory so relative content globs in tailwind.config.js
# resolve correctly (../../apps/**/templates/**/*.html → /app/apps/...)
RUN mkdir -p theme/static/css/dist && \
    cd theme/static_src && \
    npx tailwindcss \
      --input  src/styles.css \
      --output ../static/css/dist/styles.css \
      --minify


# ── Stage 2: Python application ───────────────────────────────────────────────
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies before copying the rest of the source (better layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Overwrite the placeholder CSS with the compiled version from the builder stage
COPY --from=css-builder /app/theme/static/css/dist/styles.css \
    theme/static/css/dist/styles.css

# Create a non-root runtime user
RUN useradd --uid 1001 --no-create-home --shell /bin/false appuser \
    && mkdir -p staticfiles media \
    && chown -R appuser:appuser /app \
    && chmod +x /app/docker/web/entrypoint.sh

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/accounts/login/')" || exit 1

ENTRYPOINT ["/app/docker/web/entrypoint.sh"]
