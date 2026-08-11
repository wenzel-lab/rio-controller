# Graphify setup — rio-controller

Official tool: [graphify.net](https://graphify.net/) · [GitHub](https://github.com/safishamsi/graphify)

## One-time install (PC Ubuntu)

```bash
# Recommended (puts `graphify` on PATH):
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install graphifyy

# Or project venv (already on this machine):
python3 -m venv ~/.venv-graphify
~/.venv-graphify/bin/pip install graphifyy --only-binary=:all:
```

Use the env helper before any graphify command:

```bash
source ~/rio-controller/software/scripts/graphify-env.sh
```

## Project integration (already done)

| Step | Command | What it does |
|------|---------|-------------|
| Cursor always-on | `graphify cursor install` | `.cursor/rules/graphify.mdc` — every chat uses the graph |
| Git auto-update (code) | `graphify hook install` | After each `git commit`, rebuilds AST graph in background |
| Skill in Cursor | `graphify install --platform cursor` | Same as `cursor install` |
| Global skill (optional) | copy to `~/.cursor/skills/graphify/` | Enables `/graphify` workflow in any project |

Verify:

```bash
graphify hook status
cat .cursor/rules/graphify.mdc
```

## How updates work when you change code

| When | What runs | LLM cost |
|------|-----------|----------|
| **During a Cursor session** (rule says so) | `graphify update .` | None (AST only) |
| **After `git commit`** (hook) | Background rebuild of changed `.py` files | None |
| **After branch switch** (hook) | Full code rebuild if `graphify-out/` exists | None |
| **Docs / PDF / images changed** | `/graphify --update` in Cursor, or `graphify extract … --backend claude-cli` | Uses Claude/Gemini |

The hook log: `~/.cache/graphify-rebuild.log`

## Initial full graph build

```bash
cd ~/rio-controller
source software/scripts/graphify-env.sh

# Full pipeline (semantic via Claude subscription, no GEMINI key):
graphify extract . --backend claude-cli --max-concurrency 1
graphify export html
```

Progress log: `graphify-out/extract-claude-cli.log`

## Daily use in Cursor

1. Open **`~/rio-controller`** in Cursor (not only flow-microscopy-platform docs).
2. Ask architecture questions — the agent should run `graphify query "…"` first.
3. After editing Python files, run `graphify update .` (or commit and let the hook run).

## Team / git

Per upstream README, commit `graphify-out/graph.json` + `GRAPH_REPORT.md` + `graph.html` so everyone shares the same map.

Add to `.gitignore` (optional, local-only files):

```
graphify-out/manifest.json
graphify-out/cost.json
graphify-out/extract-claude-cli.log
```

## Completar semántica con Gemini (gratis)

Para los **51 archivos** que fallaron con `claude-cli` (límite de uso):

### 1. Crear API key (sin tarjeta)

1. Abre [Google AI Studio → API keys](https://aistudio.google.com/apikey)
2. Inicia sesión con tu cuenta Google
3. **Create API key** → proyecto nuevo o existente
4. **No actives billing** en Google Cloud si te lo pide (opcional para free tier)
5. Copia la key (empieza por `AIza...`)

### 2. Instalar soporte Gemini (una vez, ya hecho en este PC)

```bash
~/.venv-graphify/bin/pip install google-genai
```

### 3. Ejecutar extract

```bash
export GEMINI_API_KEY="AIza..."   # tu key — no la commitees
source ~/rio-controller/software/scripts/graphify-env.sh
~/rio-controller/software/scripts/graphify-extract-gemini.sh
```

O manualmente:

```bash
cd ~/rio-controller
export GEMINI_API_KEY="AIza..."
export PATH="$HOME/.venv-graphify/bin:$PATH"
graphify extract . --backend gemini --max-concurrency 1 --token-budget 30000
graphify export html
```

Log: `graphify-out/extract-gemini.log` · Progreso: `graphify-out/progress.sh`

**Modelo:** graphify usa Flash por defecto (free tier). **Coste esperado: $0** si no activas facturación.

## Estado Daheng MER2 (2026-08-11)

**C++ path en `master`** (`RIO_DAHENG_CPP=1`)
- Native `libdaheng_grabber.so` + GXDQAllBufs; open = UserSet Default (Galaxy)
- Preview estable; Acq alto con exposición corta; Disp ~30
- Ramas en remoto: `feature/daheng-cpp-acq-grabber`, `feature/daheng-python-acq-ab`
- Notas: `software/docs/daheng-cpp-galaxy-notes.md`
- Graphify: `graphify update .` → **6735 nodos**, 13395 edges (2026-08-11)

## Estado Daheng MER2 (2026-06-01)

**Hecho entonces**
- ROI hardware (cola en capture thread) + snap min/max en UI
- Telemetría FPS / exposición en Camera Feed
- Exposición manual vía Galaxy `ExposureAuto=Off` + `ExposureTime` (patrón `ExposureGain.cpp`, sin `stream_off`)
- Strobe PIC-paced ya no pisa `ShutterSpeed` en Daheng
- Fix cámara blanca al cambiar tipo (`camera_controller.py`)
- Graphify: `graphify update .` → 6279 nodos (2026-06-01)

**Probar mañana**
- ROI con `RIO_ROI_MODE=hardware` (drag + release, sin freeze)
- Exposición en varios valores; confirmar FPS medido baja al subir µs
- Hard refresh UI (`Ctrl+Shift+R`) si falta control de exposición

**Arrancar Rio (PC Ubuntu + MER2)**
```bash
export GALAXY_ROOT="$HOME/Galaxy_camera"
export LD_LIBRARY_PATH="$GALAXY_ROOT/lib/x86_64:$LD_LIBRARY_PATH"
export PYTHONPATH="$HOME/rio-controller/software"
export RIO_CAMERA_TYPE=daheng RIO_DAHENG_SN=FDQ23120254
source ~/rio-controller/.venv-daheng/bin/activate
cd ~/rio-controller/software && python3 main.py
# UI: http://localhost:5000
```

**Archivos tocados (sin commit aún)**
`software/controllers/camera.py`, `strobe_cam.py`, `drivers/camera/daheng_camera.py`, `rio-webapp/templates/index.html`, `roi_selector_range.js`, `camera_controller.py`, `view_model.py`

**Siguiente paso sugerido**
Commit cuando quieras; el hook `post-commit` actualiza graphify solo. Luego validar ROI hardware en cámara real.
