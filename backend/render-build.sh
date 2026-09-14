#!/usr/bin/env bash
# Render build script for the bis-sahayak service (rootDir: backend).
#
# 1. Installs Python deps
# 2. Builds the React frontend (needs Node — Render Python runtimes include it)
# 3. Copies frontend/dist into backend/static so FastAPI serves the SPA
set -euo pipefail

echo "==> Installing Python dependencies"
pip install --no-cache-dir -r requirements.txt

echo "==> Building frontend"
cd ..
# Portable Node setup: use system node if present, else download a portable copy.
if ! command -v node >/dev/null 2>&1; then
  echo "    Node not found - downloading portable Node 20"
  curl -fsSL https://nodejs.org/dist/v20.18.1/node-v20.18.1-linux-x64.tar.xz -o /tmp/node.tar.xz
  mkdir -p /opt/node
  tar -xJf /tmp/node.tar.xz -C /opt/node --strip-components=1
  export PATH="/opt/node/bin:$PATH"
fi
node --version
npm --version

cd frontend
if [ -f package-lock.json ]; then npm ci; else npm install; fi
npm run build

echo "==> Copying dist into backend/static"
mkdir -p ../backend/static
rm -rf ../backend/static
cp -r dist ../backend/static

echo "==> Build complete"
