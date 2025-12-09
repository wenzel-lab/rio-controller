# File Location Update

## Summary

Configuration files and scripts have been moved from the repository root to the `software/` directory, where the code is executed from.

## Files Moved

1. **`rio-config.yaml`** → `software/rio-config.yaml`
2. **`setup-simulation.sh`** → `software/setup-simulation.sh`
3. **`run-simulation.sh`** → `software/run-simulation.sh`

## Rationale

Since all code execution happens from the `software/` directory, it makes logical sense to have:
- Configuration files in the same directory as the code
- Setup and run scripts in the same directory as the code
- All software-related files together for better organization

## Updated Scripts

### `setup-simulation.sh`
- Now uses `SOFTWARE_DIR` instead of `REPO_ROOT`
- Looks for `rio-config.yaml` in the current directory (`software/`)
- Creates `rio-config.yaml` in `software/` if it doesn't exist

### `run-simulation.sh`
- Now uses `SOFTWARE_DIR` instead of `REPO_ROOT`
- Runs from the `software/` directory directly
- No longer needs to navigate to `software/` subdirectory

## Usage

### Setup (first time)
```bash
cd software
./setup-simulation.sh
```

### Run simulation
```bash
cd software
./run-simulation.sh
```

Or manually:
```bash
cd software
export RIO_SIMULATION=true
python main.py
```

## Configuration

The `rio-config.yaml` file is now located in `software/rio-config.yaml`. The software will look for it in the current working directory when loading configuration.

## Documentation Updates

- `software/README.md` - Updated with new script locations
- Scripts updated to use correct directory paths
- All references verified

## Verification

- ✓ Scripts have valid syntax
- ✓ Configuration file loads correctly from new location
- ✓ All paths updated in scripts
- ✓ README updated with new usage instructions

