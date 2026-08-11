#!/usr/bin/env bash
set -euo pipefail
export PATH="${HOME}/.venv-graphify/bin:${PATH}"
cd "${HOME}/rio-controller"
[[ -f "${HOME}/.config/graphify/env" ]] && source "${HOME}/.config/graphify/env"
if [[ -z "${GEMINI_API_KEY:-}" && -z "${GOOGLE_API_KEY:-}" ]]; then
  echo "Falta GEMINI_API_KEY. Ver software/docs/graphify-setup.md" >&2
  exit 1
fi
graphify extract . --backend gemini --max-concurrency 1 --token-budget 30000
graphify cluster-only .
graphify export html
date -Iseconds > graphify-out/extract-complete.flag
echo "Graphify listo."
