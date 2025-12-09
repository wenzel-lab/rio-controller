# Port Already in Use - Quick Fix

## Problem
Port 5000 is already in use by another process.

## Solution Options

### Option 1: Kill the Process Using Port 5000

```bash
# Find and kill the process
lsof -ti:5000 | xargs kill -9

# Then run the webapp again
python pi_webapp.py
```

### Option 2: Use a Different Port

```bash
# Use port 5001 instead
python pi_webapp.py 5001

# Or set via environment variable
export RIO_PORT=5001
python pi_webapp.py
```

Then access the webapp at: **http://localhost:5001**

### Option 3: Check What's Using the Port

```bash
# See what process is using port 5000
lsof -i:5000

# You'll see output like:
# COMMAND   PID USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
# Python  12345 user   3u  IPv4  ...      0t0  TCP *:5000 (LISTEN)
```

## Updated Code

The webapp now supports:
- Command line port: `python pi_webapp.py 5001`
- Environment variable: `export RIO_PORT=5001`
- Default: port 5000

