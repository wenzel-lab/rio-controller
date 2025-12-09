# Environment Setup Guide

## ⚠️ Important: Always Use Mamba/Conda Environments

**Never install packages to system Python root!** Always use a mamba/conda environment to avoid polluting your system Python installation.

## Quick Setup

### 1. Create Mamba Environment

```bash
# Create environment with Python 3.10
mamba create -n rio-controller python=3.10 -y

# Activate environment
mamba activate rio-controller
```

### 2. Install Dependencies

```bash
cd software

# For Raspberry Pi 32-bit:
pip install -r requirements_32bit.txt

# For Raspberry Pi 64-bit:
pip install -r requirements_64bit.txt

# OR for simulation mode (Mac/PC/Ubuntu):
pip install -r requirements-simulation.txt
```

### 3. Verify Installation

```bash
# Check that you're using the environment Python
which python
# Should show: /path/to/mambaforge/envs/rio-controller/bin/python

# Verify packages
python -c "import flask; import flask_socketio; print('✓ Dependencies OK')"
```

## Checking for Root Installations

If you're concerned packages were installed to system Python:

```bash
# Check system Python packages
/usr/local/bin/pip3 list

# Check if Flask or other packages are installed there
/usr/local/bin/pip3 list | grep -i flask

# If found, you can uninstall (but be careful - other projects might use them)
# /usr/local/bin/pip3 uninstall <package-name>
```

## Best Practices

1. **Always activate environment first**:
   ```bash
   mamba activate rio-controller
   ```

2. **Verify environment before installing**:
   ```bash
   which python  # Should show mamba environment path
   which pip     # Should show mamba environment path
   ```

3. **Use environment-specific commands**:
   ```bash
   # Good - uses environment Python
   python main.py
   
   # Bad - might use system Python
   python3 main.py  # Only if python3 points to environment
   ```

4. **Check before running**:
   ```bash
   echo $CONDA_DEFAULT_ENV  # Should show: rio-controller
   ```

## Troubleshooting

**"Command not found: mamba"**:
- Install mamba: `conda install mamba -n base -c conda-forge`
- Or use `conda` instead of `mamba` (slower but works the same)

**Packages installed to wrong location**:
- Deactivate all environments: `conda deactivate`
- Check: `which python` should show system Python
- If packages were installed to root, uninstall carefully
- Reinstall in correct environment

**Environment not activating**:
```bash
# Initialize conda for your shell
conda init zsh  # or bash, fish, etc.
# Restart terminal or: source ~/.zshrc
```

## Updating Scripts

The setup scripts (`setup-simulation.sh`, `run-simulation.sh`) already use mamba/conda correctly. Always run them from within an activated environment or let them handle activation.

