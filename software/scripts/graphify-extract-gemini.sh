#!/usr/bin/env bash
# Complete semantic graphify via Google Gemini free tier (Flash model).
# Prereq: export GEMINI_API_KEY from https://aistudio.google.com/apikey
set -euo pipefail

export PATH="${HOME}/.venv-graphify/bin:${PATH}"

if [[ -z "${GEMINI_API_KEY:-}" && -z "${GOOGLE_API_KEY:-}" ]]; then
  echo "Falta GEMINI_API_KEY. Obtén una gratis en:" >&2
  echo "  https://aistudio.google.com/apikey" >&2
  echo "Luego: export GEMINI_API_KEY='tu-key'" >&2
  exit 1
fi

ROOT="${HOME}/rio-controller"
LOG="${ROOT}/graphify-out/extract-gemini.log"
cd "$ROOT"

echo "=== graphify extract (gemini, free Flash) $(date -Iseconds) ===" | tee -a "$LOG"
graphify extract . \
  --backend gemini \
  --max-concurrency 1 \
  --token-budget 30000 \
  2>&1 | tee -a "$LOG"

echo "=== export html ===" | tee -a "$LOG"
graphify export html 2>&1 | tee -a "$LOG"

date -Iseconds > "${ROOT}/graphify-out/extract-complete.flag"
echo "Listo. Abre: ${ROOT}/graphify-out/graph.html"
