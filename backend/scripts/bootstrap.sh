#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

echo "Installing frontend dependencies..."
pnpm install

echo "Installing backend dependencies..."
cd "$ROOT_DIR/backend"
uv sync

echo "Bootstrap complete."
