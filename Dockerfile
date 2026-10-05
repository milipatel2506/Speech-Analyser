# Cadence: one container serving the API and the built dashboard on port 8000.
#   docker build -t cadence .
#   docker run -p 8000:8000 -v cadence-models:/home/user/models cadence      -> http://localhost:8000
# Also runs unchanged as a Hugging Face Docker Space (non-root user 1000, app_port 8000).
# If dataset audio is not in the image, it is downloaded from DATASET_REPO at start-up.
# The forced-alignment model (~1.2 GB) downloads on first analysis into TORCH_HOME.

FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg libsndfile1 \
 && rm -rf /var/lib/apt/lists/* \
 && pip install --no-cache-dir uv==0.12.23 \
 && useradd -m -u 1000 user

USER user
ENV HOME=/home/user \
    UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 \
    TORCH_HOME=/home/user/models HF_HOME=/home/user/models/hf \
    DATASET_REPO=milipatel2506/cadence-contrastive-speech
WORKDIR /home/user/app

COPY --chown=user pyproject.toml uv.lock README.md .python-version ./
COPY --chown=user src ./src
RUN uv sync --frozen --no-dev

COPY --chown=user scripts ./scripts
COPY --chown=user dataset ./dataset
COPY --chown=user docs ./docs
COPY --chown=user --from=web /web/dist ./frontend/dist

EXPOSE 8000
CMD ["sh", "-c", "[ -d dataset/audio/baseline ] || uv run --no-sync python scripts/hf_dataset.py download --repo \"$DATASET_REPO\"; exec uv run --no-sync uvicorn speech_analyser.api.main:app --app-dir src --host 0.0.0.0 --port 8000"]
