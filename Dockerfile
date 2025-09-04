# ---------- FRONTEND (unchanged except minor hygiene) ----------
FROM node:22-alpine AS frontend

WORKDIR /usr/src/app/frontend

# (Optional but recommended) toolchain for native Node modules
# RUN apk add --no-cache python3 make g++ git libc6-compat

# Copy only manifests first for better layer caching
# If you have lockfile:
# COPY ./frontend/package.json ./frontend/package-lock.json ./
# Otherwise fall back to copying whole folder as you had:
COPY ./frontend ./ 

# Deterministic install if you have package-lock.json:
# RUN npm ci
# If not, keep npm install:
RUN npm install \
  && npm run build \
  && rm -rf node_modules


# ---------- VENV (Python 3.12 with uv) ----------
FROM ghcr.io/astral-sh/uv:python3.12-bookworm AS venv

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
     build-essential libmagic-dev libffi-dev python3-dev libssl-dev pkg-config git \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

# Use uv only (more reproducible) — no pip install here
COPY pyproject.toml uv.lock ./

# Build a project-local venv from the lock (no dev deps)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --python-preference=only-managed


# ---------- RUNTIME (Python 3.12) ----------
FROM python:3.12-slim-bookworm

RUN apt-get update \
  && apt-get install -y --no-install-recommends libmagic-dev spamd \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# If rule freshness baked into image matters to you:
RUN sa-update --no-gpg || true

WORKDIR /usr/src/app

# Frontend built artifacts
# (You’re copying the entire frontend directory as before.)
COPY --from=frontend /usr/src/app/frontend ./frontend

# Bring in the prebuilt virtualenv
COPY --from=venv /usr/src/app/.venv ./.venv
ENV PATH="/usr/src/app/.venv/bin:${PATH}"

# App config & code
COPY gunicorn.conf.py circus.ini ./
COPY backend ./backend

# Environment
ENV SPAMD_MAX_CHILDREN=1
ENV SPAMD_PORT=7833
ENV SPAMD_RANGE="10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,127.0.0.1/32"
ENV SPAMASSASSIN_PORT=7833
ENV PORT=8000

CMD ["circusd", "/usr/src/app/circus.ini"]