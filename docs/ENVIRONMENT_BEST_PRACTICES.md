# Environment Best Practices

## ⚠️ Critical: Never Install to System Python Root

**Always use mamba/conda environments** to avoid polluting your system Python installation.

## Why This Matters

1. **System Stability**: Installing packages to root Python can break system tools
2. **Version Conflicts**: Different projects need different package versions
3. **Clean Isolation**: Each project should have its own environment
4. **Easy Cleanup**: Delete environment = remove all packages

## How to Check if Packages Were Installed to Root

```bash
# Check system Python packages
/usr/local/bin/pip3 list

# Check for specific packages
/usr/local/bin/pip3 list | grep -E "flask|opencv|numpy"

# If you find packages you didn't intend to install there:
# 1. Check if other projects need them
# 2. If safe, uninstall: /usr/local/bin/pip3 uninstall <package>
```

## Safe Installation Workflow

### Always Follow This Pattern:

```bash
# 1. Create/activate environment FIRST
mamba create -n rio-controller python=3.10 -y
mamba activate rio-controller

# 2. Verify you're in the environment
which python  # Should show: .../mambaforge/envs/rio-controller/bin/python
echo $CONDA_DEFAULT_ENV  # Should show: rio-controller

# 3. THEN install packages
pip install -r requirements.txt

# 4. Verify installation location
pip show flask  # Location should be in mamba environment path
```

## What I've Done (No Root Installations)

**Important**: I have **NOT** run any `pip install` commands. I've only:
- Tested imports with `python -c "import ..."` (doesn't install anything)
- Updated documentation
- Moved files around

**No packages were installed to root by my actions.**

## Future Safety Measures

1. **All documentation updated** to emphasize mamba environments
2. **Setup scripts verify environment** before installing
3. **README emphasizes** environment activation
4. **New ENVIRONMENT_SETUP.md** created with best practices

## If You Accidentally Installed to Root

If you accidentally ran `pip install` without an activated environment:

```bash
# 1. Check what was installed
/usr/local/bin/pip3 list

# 2. If safe to remove (check dependencies first):
/usr/local/bin/pip3 uninstall <package-name>

# 3. Reinstall in correct environment
mamba activate rio-controller
pip install <package-name>
```

## Verification Commands

Before running any installation:

```bash
# Check active environment
echo $CONDA_DEFAULT_ENV

# Check Python location
which python

# Check pip location
which pip

# All should point to your mamba environment, not system paths
```

