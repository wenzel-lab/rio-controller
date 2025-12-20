# Copying Code from Raspberry Pi to Mac/PC

This guide explains how to copy the code from your Raspberry Pi back to your computer for analysis and updates.

---

## Method 1: Using rsync (Recommended)

`rsync` is the best tool for this because it:
- Only copies changed files (faster)
- Preserves permissions and timestamps
- Can resume if interrupted
- Shows progress

### Step 1: Create a destination directory on your Mac

```bash
# Create a directory to store the Pi code snapshot
mkdir -p ~/pi-code-snapshots
cd ~/pi-code-snapshots

# Create a dated directory for this snapshot
mkdir pi-snapshot-$(date +%Y%m%d-%H%M%S)
cd pi-snapshot-$(date +%Y%m%d-%H%M%S)
```

Or simpler, just create one directory:

```bash
mkdir -p ~/pi-code-analysis
cd ~/pi-code-analysis
```

### Step 2: Copy the code using rsync

**Basic rsync command:**

```bash
rsync -avz --progress pi@raspberrypi.local:~/rio-controller/ ~/pi-code-analysis/pi-code/
```

**Or with IP address:**

```bash
rsync -avz --progress pi@192.168.1.XXX:~/rio-controller/ ~/pi-code-analysis/pi-code/
```

**What this does:**
- `-a`: Archive mode (preserves permissions, timestamps, symbolic links)
- `-v`: Verbose (shows files being copied)
- `-z`: Compress during transfer (faster over network)
- `--progress`: Show progress for each file
- `pi@raspberrypi.local:~/rio-controller/`: Source on Pi
- `~/pi-code-analysis/pi-code/`: Destination on your Mac

**Expected output:**
```
receiving incremental file list
./
main.py
config.py
setup.sh
...
pi-code/
    main.py                       100%  1234    1.2KB/s   00:01
    config.py                     100%  5678    5.7KB/s   00:01
    ...
```

### Step 3: Verify the copy

```bash
# List what was copied
ls -la ~/pi-code-analysis/pi-code/

# Check if main files are there
ls ~/pi-code-analysis/pi-code/main.py
ls ~/pi-code-analysis/pi-code/controllers/
ls ~/pi-code-analysis/pi-code/drivers/
```

---

## Method 2: Using scp (Simple Alternative)

If `rsync` is not available or you prefer a simpler tool:

### Copy entire directory:

```bash
# Create destination directory
mkdir -p ~/pi-code-analysis

# Copy entire directory recursively
scp -r pi@raspberrypi.local:~/rio-controller ~/pi-code-analysis/pi-code
```

**What this does:**
- `-r`: Recursive (copies directories and subdirectories)
- `pi@raspberrypi.local:~/rio-controller`: Source on Pi
- `~/pi-code-analysis/pi-code`: Destination on Mac

**Note:** `scp` will copy everything each time, unlike `rsync` which only copies changes.

---

## Method 3: Create a tarball on Pi, then copy

This is useful if you want to compress everything first:

### Step 1: On Pi (via SSH)

```bash
ssh pi@raspberrypi.local

# Create compressed tarball
cd ~
tar czf rio-controller-backup.tar.gz rio-controller/

# Exit SSH session
exit
```

### Step 2: Copy tarball to Mac

```bash
# Copy tarball to Mac
scp pi@raspberrypi.local:~/rio-controller-backup.tar.gz ~/pi-code-analysis/

# Extract on Mac
cd ~/pi-code-analysis
tar xzf rio-controller-backup.tar.gz

# Clean up tarball (optional)
rm rio-controller-backup.tar.gz
```

---

## Recommended Workflow for Analysis

### Option A: Copy to a separate analysis directory (Recommended)

This keeps your working repository clean:

```bash
# 1. Create analysis directory
mkdir -p ~/pi-code-analysis
cd ~/pi-code-analysis

# 2. Copy from Pi
rsync -avz --progress pi@raspberrypi.local:~/rio-controller/ ./pi-code/

# 3. Compare with your working repo (if needed)
# Your working repo is in: /Users/twenzel/Documents/GitHub/open-microfluidics-workstation
```

### Option B: Copy into your working repository

If you want to compare directly in your repository:

```bash
# Copy to a subdirectory in your repo
cd /Users/twenzel/Documents/GitHub/open-microfluidics-workstation
mkdir -p pi-snapshot
rsync -avz --progress pi@raspberrypi.local:~/rio-controller/ ./pi-snapshot/
```

---

## What Gets Copied

When copying `~/rio-controller/` from the Pi, you'll get:

```
pi-code/
├── main.py
├── config.py
├── setup.sh
├── run.sh
├── requirements-webapp-only-32bit.txt
├── README.md
├── controllers/
│   ├── camera.py
│   ├── strobe_cam.py
│   └── ...
├── drivers/
│   ├── camera/
│   ├── strobe.py
│   └── ...
├── droplet-detection/
├── rio-webapp/
│   ├── controllers/
│   ├── static/
│   ├── templates/
│   └── routes.py
├── configurations/
└── venv-rio/          # Virtual environment (optional - usually excluded)
```

**Note:** You probably don't need the `venv-rio/` directory (it's large and environment-specific). See "Excluding Files" below.

---

## Excluding Unnecessary Files

### Exclude virtual environment

The `venv-rio/` directory is large and environment-specific. Exclude it:

```bash
rsync -avz --progress --exclude 'venv-rio' \
  pi@raspberrypi.local:~/rio-controller/ ~/pi-code-analysis/pi-code/
```

### Exclude multiple patterns

```bash
rsync -avz --progress \
  --exclude 'venv-rio' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '*.pyo' \
  pi@raspberrypi.local:~/rio-controller/ ~/pi-code-analysis/pi-code/
```

### Using .gitignore-style exclusions file

Create a file `rsync-exclude.txt`:

```
venv-rio/
__pycache__/
*.pyc
*.pyo
.DS_Store
*.log
```

Then use it:

```bash
rsync -avz --progress --exclude-from='rsync-exclude.txt' \
  pi@raspberrypi.local:~/rio-controller/ ~/pi-code-analysis/pi-code/
```

---

## Troubleshooting

### Issue: "Could not resolve hostname raspberrypi.local"

**Solution:** Use IP address instead:

```bash
# Find IP first (if needed)
ping raspberrypi.local

# Or use IP directly
rsync -avz --progress pi@192.168.1.XXX:~/rio-controller/ ~/pi-code-analysis/pi-code/
```

### Issue: Permission denied

**Solution:** Make sure you can SSH into the Pi:

```bash
# Test SSH connection first
ssh pi@raspberrypi.local

# If that works, rsync should work too
```

### Issue: rsync not found

**Solution:** Install rsync (usually pre-installed on macOS):

```bash
# Check if rsync exists
which rsync

# If not, install via Homebrew (if you have it)
brew install rsync

# Or use scp method instead
```

### Issue: Large file transfer is slow

**Solutions:**
1. Use compression: `-z` flag (already in command)
2. Use wired Ethernet connection if possible
3. Compress first with tarball method (Method 3)
4. Exclude unnecessary files (venv, cache files)

---

## Next Steps After Copying

1. **Compare files:**
   ```bash
   # Use diff to compare specific files
   diff ~/pi-code-analysis/pi-code/main.py /path/to/repo/software/main.py
   
   # Or use a GUI tool like VS Code
   code --diff ~/pi-code-analysis/pi-code/main.py /path/to/repo/software/main.py
   ```

2. **Note manual changes:**
   - Document any manual edits you made on the Pi
   - Document any configuration changes
   - Document any package version differences

3. **Update repository:**
   - Apply necessary fixes to the repository code
   - Update installation instructions based on issues found
   - Update deployment scripts if needed

4. **Create a changelog:**
   - Document what had to be changed on the Pi
   - Note why changes were necessary
   - Update deployment documentation

---

## Quick Reference Commands

### Basic copy (recommended):

```bash
rsync -avz --progress --exclude 'venv-rio' \
  pi@raspberrypi.local:~/rio-controller/ ~/pi-code-analysis/pi-code/
```

### Copy with IP address:

```bash
rsync -avz --progress --exclude 'venv-rio' \
  pi@192.168.1.XXX:~/rio-controller/ ~/pi-code-analysis/pi-code/
```

### Simple scp copy:

```bash
scp -r pi@raspberrypi.local:~/rio-controller ~/pi-code-analysis/pi-code
```

### Tarball method:

```bash
# On Pi (via SSH)
ssh pi@raspberrypi.local "cd ~ && tar czf rio-controller-backup.tar.gz rio-controller/"

# Copy to Mac
scp pi@raspberrypi.local:~/rio-controller-backup.tar.gz ~/pi-code-analysis/

# Extract
cd ~/pi-code-analysis && tar xzf rio-controller-backup.tar.gz
```

---

## Tips

1. **Create dated snapshots** if you want to compare multiple versions:
   ```bash
   SNAPSHOT_DIR=~/pi-code-snapshots/$(date +%Y%m%d-%H%M%S)
   mkdir -p $SNAPSHOT_DIR
   rsync -avz --progress --exclude 'venv-rio' \
     pi@raspberrypi.local:~/rio-controller/ $SNAPSHOT_DIR/
   ```

2. **Use VS Code's compare feature** to easily see differences between files

3. **Document manual changes** in a text file as you make them on the Pi, so you remember what to update in the repo

4. **Keep the Pi code as-is** until you've fully analyzed it - don't delete it from the Pi until you're done
