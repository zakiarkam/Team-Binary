# API image for Railway / Render / Fly.io.
#
# Two things make this bigger than a normal FastAPI image, and both are
# deliberate: PyTorch (Module 4's sentence embeddings) and XGBoost (Module 3's
# predictions) ship inside the container so the API can serve model inference
# without a second service. Budget ~2 GB RAM on the host.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    # macOS needs this to stop torch and xgboost fighting over OpenMP; on Linux
    # it is merely a sensible default for a single-worker web process.
    OMP_NUM_THREADS=1 \
    TOKENIZERS_PARALLELISM=false

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

# CPU-only torch. The default wheel drags in ~2 GB of CUDA that no web dyno
# can use, and several platforms fail the build on image size because of it.
COPY requirements.txt api/requirements.txt ./
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch==2.13.0 \
    && pip install -r requirements.txt -r api/requirements.txt

COPY . .

# Trained artifacts are committed, so the image can answer on first boot
# instead of training on startup.
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
    CMD curl -fsS http://localhost:${PORT:-8000}/health || exit 1

# $PORT is injected by Railway/Render/Fly; 8000 is the local default.
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
