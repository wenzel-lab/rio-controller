#!/bin/bash
# Patch ~/rio-scenario1-bullseye.img in place with current Scenario 1 files
# (no SD card required). Needs sudo once.
#
#   bash ~/rio-controller/scripts/deploy/update-rio-img-from-local.sh
set -euo pipefail

IMG="${RIO_IMG:-$HOME/rio-scenario1-bullseye.img}"
SRC="${RIO_SRC:-$HOME/rio-controller}"
# Flat layout on the image matches pi-deployment/
DEPLOY="$SRC/pi-deployment"
MNT="${TMPDIR:-/tmp}/rio-img-rootfs-$$"

[[ -f "$IMG" ]] || { echo "ERROR: image not found: $IMG"; exit 1; }
[[ -d "$DEPLOY/controllers" ]] || { echo "ERROR: missing $DEPLOY (run create-pi-deployment.sh)"; exit 1; }

# Refresh deploy bundle from software/ before patching
bash "$SRC/scripts/deploy/create-pi-deployment.sh"

echo "=== Source image ==="
ls -lh "$IMG"
echo
echo "=== Mounting rootfs (partition 2 @ sector 532480) ==="
sudo mkdir -p "$MNT"
LOOP=$(sudo losetup -f --show -P "$IMG")
echo "Loop: $LOOP"
ROOT="${LOOP}p2"
[[ -b "$ROOT" ]] || { echo "ERROR: $ROOT missing"; sudo losetup -d "$LOOP"; exit 1; }

sudo mount "$ROOT" "$MNT"
TARGET="$MNT/home/pi/rio-controller"
[[ -d "$TARGET" ]] || { echo "ERROR: $TARGET missing in image"; sudo umount "$MNT"; sudo losetup -d "$LOOP"; exit 1; }

echo "=== Syncing Scenario 1 bundle → image ==="
sudo rsync -a --delete \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.git' \
  "$DEPLOY/" "$TARGET/"

# Ensure systemd unit if present on host
if [[ -f "$SRC/scripts/pi/systemd/rio-ui.service" ]]; then
  sudo mkdir -p "$MNT/etc/systemd/system"
  sudo cp "$SRC/scripts/pi/systemd/rio-ui.service" \
    "$MNT/etc/systemd/system/rio-ui.service"
fi

# Autostart desktop entry
if [[ -f "$DEPLOY/omw.desktop" ]]; then
  sudo mkdir -p "$MNT/home/pi/.config/autostart"
  sudo cp "$DEPLOY/omw.desktop" "$MNT/home/pi/.config/autostart/omw.desktop"
  sudo chown -R 1000:1000 "$MNT/home/pi/.config/autostart" 2>/dev/null || true
fi

sudo chown -R 1000:1000 "$TARGET" 2>/dev/null || true

# Verify half-black fix is present
if ! grep -q "Re-apply strobe timing after camera start" "$TARGET/controllers/camera.py"; then
  echo "ERROR: fix string missing after sync"
  sudo umount "$MNT"
  sudo losetup -d "$LOOP"
  exit 1
fi

echo "=== Unmounting / syncing ==="
sudo sync
sudo umount "$MNT"
sudo losetup -d "$LOOP"
sudo rmdir "$MNT" 2>/dev/null || true

# Bump mtime so it is obvious this replaced the 17:15 image
touch "$IMG"

echo
echo "=== DONE — image updated in place ==="
ls -lh "$IMG"
echo "Verified: camera.py contains post-start set_timing re-apply"
echo "Image ready: $IMG"
