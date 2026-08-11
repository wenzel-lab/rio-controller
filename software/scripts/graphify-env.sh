#!/usr/bin/env bash
# Source before graphify commands in rio-controller:
#   source software/scripts/graphify-env.sh

_GRAPHIFY_VENV="${HOME}/.venv-graphify"
if [[ -x "${_GRAPHIFY_VENV}/bin/graphify" ]]; then
  export PATH="${_GRAPHIFY_VENV}/bin:${PATH}"
else
  echo "graphify: install ~/.venv-graphify or run: uv tool install graphifyy" >&2
  return 1 2>/dev/null || exit 1
fi

# When running from repo root after sourcing from software/
if [[ -f "$(pwd)/graphify-out/.graphify_python" ]]; then
  :
elif [[ -f "${HOME}/rio-controller/graphify-out/.graphify_python" ]]; then
  export GRAPHIFY_OUT="${HOME}/rio-controller/graphify-out"
fi

echo "graphify: $(command -v graphify) ($(graphify --version 2>&1 | head -1))"
