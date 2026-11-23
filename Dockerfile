# Imagem única de produção: compila o front-end React e serve tudo pelo FastAPI.
# Usada no Render e na AWS. O broker MQTT fica fora deste contêiner.

# ── Etapa 1: build do front-end ────────────────────────────────────────────
FROM node:20-alpine AS frontend
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ── Etapa 2: backend Python ────────────────────────────────────────────────
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/app backend/app
# main.py procura o build em <raiz>/frontend/dist
COPY --from=frontend /frontend/dist frontend/dist

RUN useradd --create-home appuser && mkdir -p backend/logs && chown -R appuser /app
USER appuser
WORKDIR /app/backend

# Render (e outras plataformas) informam a porta pela variável PORT
ENV PORT=8001
EXPOSE 8001
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
