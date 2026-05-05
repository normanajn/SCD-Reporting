# Stage 1: Build Tailwind CSS
FROM node:20-alpine AS css-builder

WORKDIR /app

COPY theme/static_src/ ./theme/static_src/
COPY apps/ ./apps/

WORKDIR /app/theme/static_src

RUN npm install && \
    mkdir -p ../static/css/dist && \
    npx tailwindcss --input src/styles.css --output ../static/css/dist/styles.css --minify


# Stage 2: Python application
FROM python:3.12-slim

# WeasyPrint system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p theme/static/css/dist
COPY --from=css-builder /app/theme/static/css/dist/styles.css theme/static/css/dist/styles.css

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

CMD ["sh", "-c", \
    "python manage.py migrate --noinput && \
     python manage.py collectstatic --noinput && \
     python manage.py seed_admin && \
     gunicorn scd_reporting.wsgi:application \
       --bind 0.0.0.0:8000 \
       --workers ${GUNICORN_WORKERS:-3}"]
