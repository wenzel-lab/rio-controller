## AI-generated notice

This file was AI-generated and may contain errors. Please verify against the source code and runtime behavior.
- Date: 2025-12-30
- Model: GPT-5.2
- Maintenance: If you change pipeline behavior or public interfaces, please update this document.

## Purpose

This folder contains the **droplet detection pipeline** (image preprocessing → segmentation → measurement → artifact rejection → histogram/statistics). It is used both at runtime (via the droplet detector controller) and in offline workflows (tests/benchmarks/optimization).

## What belongs here / what does not

- **Belongs here**:
  - core algorithm code and configuration objects for droplet detection
  - offline utilities that exercise the pipeline end-to-end (integration tests, benchmark/optimize)
- **Does not belong here**:
  - camera acquisition and strobe timing (belongs in `../controllers/` and `../drivers/camera/`)
  - UI event handling and Flask routes (belongs in `../rio-webapp/`)

## Naming note

This directory is named `droplet-detection` (hyphenated). Importing it as a Python module may require special handling elsewhere in the codebase.

## Entry points

- `detector.py`: primary pipeline
- `preprocessor.py`, `segmenter.py`, `measurer.py`, `artifact_rejector.py`: pipeline stages
- `histogram.py`: histogram/statistics
- `config.py`: configuration and persistence helpers

## Testing and evaluation

Run routine tests from `software/`:

```bash
cd software
export RIO_SIMULATION=true
pytest -v
```

For droplet-detection-specific tooling, see `software/tests/droplet-detection-testing_and_optimization_guide.md`.


