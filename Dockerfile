# syntax=docker/dockerfile:1.7

########## FRONTEND (build) ##########
FROM node:22-alpine AS frontend
WORKDIR /usr/src/app/frontend

# Toolchain for node-gyp/native modules on Alpine
RUN apk add --no-cache python3 make g++ git libc6-compat

# (Optional) If you use sharp/canvas, uncomment what you need:
# RUN apk add --no-cache vips-dev # for sharp
# RUN apk add --no-cache cairo pango pixman-dev jpeg-dev giflib-dev # for canvas

# Copy only manifests first for better layer caching
COPY ./frontend/package*.json ./

# Deterministic, faster installs; cache npm dir across builds
RUN --mount=type=cache,target=/root/.npm npm ci

# Now copy the rest and build
COPY ./frontend ./
# Helps avoid OOM during big builds
ENV NODE_OPTIONS=--max_old_space_size=2048
# If you're battling peer-deps temporarily:
# RUN --mount=type=cache,target=/root/.npm npm ci --legacy-peer-deps
RUN npm run build

# NOTE: Adjust the next path if your build output differs (e.g., .next, out)
# We'll export only the build artifacts later:
#   - Vite: /usr/src/app/frontend/dist
#   - Next.js static export: /usr/src/app/frontend/out
#   - React CRA: /usr/src/app/frontend/build


########## PYTHON DEPS (uv virtualenv) ##########
# Use uv image to guarantee uv availability and reproducibility
FROM ghcr.io/astral-sh/uv:python3.11-bookworm AS venv
WORKDIR /usr/src/app

# If you need system headers for building Python wheels, add them here:
RUN apt-get update \
  && apt-get install -y --no-install-recommends build-essential libmagic-dev \
  && rm -rf /var/lib/apt/lists/*

# Copy dependency metadata only (cache-friendly)
COPY pyproject.toml uv.lock ./

# Create a project-local venv with locked deps (no dev deps)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --python-preference=only-managed

########## RUNTIME ##########
FROM python:3.11-slim-bookworm AS runtime

# Runtime-only packages (no compilers)
RUN apt-get update \
  && apt-get install -y --no-install-recommends libmagic-dev spamd \
  && rm -rf /var/lib/apt/lists/*

# Update SpamAssassin rules (ok during build if you need current rules baked in)
RUN sa-update --no-gpg || true

WORKDIR /usr/src/app

# Bring in the prebuilt virtualenv
COPY --from=venv /usr/src/app/.venv ./.venv
ENV PATH="/usr/src/app/.venv/bin:${PATH}"

# Bring in only the built frontend assets (adjust path for your framework)
# Vite:
COPY --from=frontend /usr/src/app/frontend/dist ./frontend/dist
# Next.js export:
# COPY --from=frontend /usr/src/app/frontend/out ./frontend/out
# CRA:
# COPY --from=frontend /usr/src/app/frontend/build ./frontend/build

# App code & config
COPY gunicorn.conf.py circus.ini ./
COPY backend ./backend

# Your environment
ENV SPAMD_MAX_CHILDREN=1
ENV SPAMD_PORT=7833
ENV SPAMD_RANGE="10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,127.0.0.1/32"
ENV SPAMASSASSIN_PORT=7833
ENV PORT=8000

CMD ["circusd", "/usr/src/app/circus.ini"]