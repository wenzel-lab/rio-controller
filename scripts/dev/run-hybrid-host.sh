#!/usr/bin/env bash
# Run Rio UI on the CoolerMaster / Ubuntu host in hybrid mode:
#   - Local Daheng camera (+ AI/droplet on this machine)
#   - Strobe / flow / heater over the Pi FastAPI
#
# Usage:
#   ./scripts/dev/run-hybrid-host.sh
#   ./scripts/dev/run-hybrid-host.sh --pi 192.168.31.61 --port 5000
#   RIO_PI_URL=http://192.168.31.61:8000 ./scripts/dev/run-hybrid-host.sh
#
# Critical: RIO_NO_GEVENT_PATCH=true — without it, gevent monkey-patches threading
# and the Daheng capture loop starves Socket.IO (~20 s UI latency).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SOFTWARE_DIR="$REPO_ROOT/software"
VENV_PY="${RIO_VENV_PYTHON:-$REPO_ROOT/.venv-daheng/bin/python}"
GALAXY_ROOT="${GALAXY_ROOT:-$HOME/Galaxy_camera}"

PI_URL="${RIO_PI_URL:-${RIO_REMOTE_API_URL:-http://192.168.31.61:8000}}"
PORT="${RIO_PORT:-5000}"
BACKGROUND=0
STOP_EXISTING=1

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

  --pi URL|HOST   Pi FastAPI base (default: $PI_URL)
                  Examples: 192.168.31.61  or  http://192.168.31.61:8000
  --port N        UI port (default: $PORT)
  --fg            Run in foreground (default)
  --bg            Run in background (log: /tmp/rio_hybrid_host.log)
  --no-kill       Do not kill whatever is already on --port
  -h, --help      Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --pi)
      PI_URL="$2"
      shift 2
      ;;
    --port)
      PORT="$2"
      shift 2
      ;;
    --bg)
      BACKGROUND=1
      shift
      ;;
    --fg)
      BACKGROUND=0
      shift
      ;;
    --no-kill)
      STOP_EXISTING=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

# Allow bare host/IP for --pi
if [[ "$PI_URL" != http://* && "$PI_URL" != https://* ]]; then
  PI_URL="http://${PI_URL}"
fi
if [[ "$PI_URL" != *:8000 && "$PI_URL" != *:8000/* ]]; then
  # host only → assume FastAPI on 8000
  if [[ "$PI_URL" =~ ^https?://[^/:]+$ ]]; then
    PI_URL="${PI_URL}:8000"
  fi
fi
PI_URL="${PI_URL%/}"

if [[ ! -x "$VENV_PY" ]]; then
  echo "Error: Python venv not found/executable: $VENV_PY" >&2
  echo "Create it or set RIO_VENV_PYTHON=/path/to/python" >&2
  exit 1
fi

if [[ ! -d "$GALAXY_ROOT" ]]; then
  echo "Warning: GALAXY_ROOT missing ($GALAXY_ROOT) — Daheng SDK libs may fail to load" >&2
fi

if [[ "$STOP_EXISTING" -eq 1 ]]; then
  if command -v ss >/dev/null 2>&1; then
    OLD_PID="$(ss -ltnpH "sport = :${PORT}" 2>/dev/null | grep -o 'pid=[0-9]*' | head -1 | cut -d= -f2 || true)"
    if [[ -n "${OLD_PID:-}" ]]; then
      echo "Stopping existing process on :${PORT} (pid $OLD_PID)"
      kill "$OLD_PID" 2>/dev/null || true
      sleep 2
      kill -9 "$OLD_PID" 2>/dev/null || true
      sleep 1
    fi
  fi
fi

export GALAXY_ROOT
export LD_LIBRARY_PATH="${GALAXY_ROOT}/lib/x86_64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export RIO_SIMULATION=false
export RIO_NO_GEVENT_PATCH=true
export RIO_SKIP_SPI=1
export RIO_REMOTE_MODULES="${RIO_REMOTE_MODULES:-strobe,flow,heater}"
export RIO_REMOTE_API_URL="$PI_URL"
export RIO_FASTAPI_BASE_URL="$PI_URL"
export RIO_LOG_LEVEL="${RIO_LOG_LEVEL:-INFO}"

cd "$SOFTWARE_DIR"

echo "============================================"
echo " Rio hybrid host (CoolerMaster / Ubuntu)"
echo "============================================"
echo " Python:     $VENV_PY"
echo " Galaxy:     $GALAXY_ROOT"
echo " UI:         http://0.0.0.0:${PORT}"
echo " Pi API:     $PI_URL"
echo " Remote:     $RIO_REMOTE_MODULES"
echo " Gevent:     PATCH OFF (RIO_NO_GEVENT_PATCH=true)"
echo " SPI:        skipped (RIO_SKIP_SPI=1)"
echo "============================================"

if [[ "$BACKGROUND" -eq 1 ]]; then
  LOG=/tmp/rio_hybrid_host.log
  # shellcheck disable=SC2086
  setsid nohup "$VENV_PY" main.py "$PORT" >"$LOG" 2>&1 < /dev/null &
  echo "Started in background (pid $!). Log: $LOG"
  echo "Open: http://127.0.0.1:${PORT}"
else
  echo "Press Ctrl+C to stop"
  echo ""
  exec "$VENV_PY" main.py "$PORT"
fi
