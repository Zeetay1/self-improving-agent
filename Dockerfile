# Hugging Face Spaces (Docker SDK) image for the FastAPI backend.
# Spaces routes traffic to port 7860 by default.
FROM python:3.11-slim

# System libraries needed at runtime by torch (OpenMP via libgomp) and by
# chromadb/onnxruntime; ca-certificates for HTTPS model downloads.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgomp1 \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Use the PyTorch backend only; never import TensorFlow/Keras in transformers.
ENV USE_TF=0 \
    USE_TORCH=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install Python deps first so this layer caches across code changes.
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the rest of the project (the .dockerignore keeps secrets/db/web out).
COPY . .

EXPOSE 7860

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860"]
