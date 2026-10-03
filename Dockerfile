# ============================================================
# JEWELMATCH AI - DOCKERFILE
# ============================================================

# ============================================================
# STAGE 1 - BUILD REACT FRONTEND
# ============================================================

FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend/react

# Copy package files first for Docker layer caching
COPY frontend/react/package*.json ./

RUN npm install

# Copy React source
COPY frontend/react/ ./

# Build production frontend
RUN npm run build


# ============================================================
# STAGE 2 - PYTHON BACKEND
# ============================================================

FROM python:3.11-slim

WORKDIR /app


# ============================================================
# SYSTEM DEPENDENCIES
# ============================================================

RUN apt-get update && apt-get install -y \
    curl \
    libglib2.0-0 \
    libgl1 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*


# ============================================================
# PYTHON ENVIRONMENT
# ============================================================

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1


# ============================================================
# PYTHON DEPENDENCIES
# ============================================================

COPY backend/requirements.txt ./backend/requirements.txt

RUN pip install --no-cache-dir \
    --upgrade pip

# Install CPU version of PyTorch
RUN pip install --no-cache-dir \
    torch \
    --index-url https://download.pytorch.org/whl/cpu

# Install project dependencies
RUN pip install --no-cache-dir \
    -r backend/requirements.txt


# ============================================================
# COPY PROJECT
# ============================================================

COPY backend ./backend

# Copy production React build
COPY --from=frontend-builder \
    /app/frontend/react/dist \
    ./frontend/react/dist


# ============================================================
# CREATE REQUIRED DIRECTORIES
# ============================================================

RUN mkdir -p \
    backend/database/uploads \
    backend/database \
    backend/catalogue/gold \
    backend/catalogue/prototype


# ============================================================
# RENDER PORT
# ============================================================

ENV PORT=10000

EXPOSE 10000


# ============================================================
# START APPLICATION
# ============================================================

CMD gunicorn \
    --bind 0.0.0.0:${PORT} \
    --workers 1 \
    --threads 2 \
    --timeout 300 \
    backend.app:app