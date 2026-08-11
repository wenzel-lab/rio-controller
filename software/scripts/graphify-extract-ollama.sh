#!/usr/bin/env bash
# Complete semantic graphify for rio-controller using local Ollama (no Claude/Gemini quota).
set -euo pipefail

export PATH="${HOME}/.venv-graphify/bin:${PATH}"
export OLLAMA_API_KEY="${OLLAMA_API_KEY:-local}"
export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://127.0.0.1:11434/v1}"
export OLLAMA_MODEL="${OLLAMA_MODEL:-qwen2.5-coder:7b}"
# One chunk at a time — Ollama serves one heavy request per GPU
export GRAPHIFY_OLLAMA_PARALLEL="${GRAPHIFY_OLLAMA_PARALLEL:-0}"

ROOT="${HOME}/rio-controller"
LOG="${ROOT}/graphify-out/extract-ollama.log"

cd "$ROOT"

if ! command -v ollama >/dev/null; then
  echo "Install Ollama: curl -fsSL https://ollama.com/install.sh | sh" >&2
  exit 1
fi

if ! curl -sf "${OLLAMA_BASE_URL%/v1}/api/tags" >/dev/null 2>&1; then
  echo "Starting ollama serve..."
  ollama serve >/dev/null 2>&1 &
  sleep 3
fi

echo "Pulling model ${OLLAMA_MODEL} (once)..."
ollama pull "${OLLAMA_MODEL}"

echo "Extract started $(date -Iseconds) → ${LOG}"
graphify extract . \
  --backend ollama \
  --max-concurrency 1 \
  --token-budget 30000 \
  2>&1 | tee -a "${LOG}"

graphify export html 2>&1 | tee -a "${LOG}"
date -Iseconds > "${ROOT}/graphify-out/extract-complete.flag"
echo "Done $(date -Iseconds)"
