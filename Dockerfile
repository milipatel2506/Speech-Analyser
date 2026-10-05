# Cadence: one container serving the API and the built dashboard on port 8000.
#   docker build -t cadence .
#   docker run -p 8000:8000 -v cadence-models:/models cadence
# The forced-alignment model (~1.2 GB) downloads on first analysis into the /models volume.

FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg libsndfile1 \
 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv==0.12.23

WORKDIR /app
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 TORCH_HOME=/models HF_HOME=/models/hf
COPY pyproject.toml uv.lock README.md .python-version ./
COPY src ./src
RUN uv sync --frozen --no-dev

COPY scripts ./scripts
COPY dataset ./dataset
COPY docs ./docs
COPY --from=web /web/dist ./frontend/dist

EXPOSE 8000
CMD ["uv", "run", "--no-sync", "uvicorn", "speech_analyser.api.main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]
