#!/bin/bash
# Create a bootable Rio Scenario-1 disk image from the USB SD reader.
# Fast path: local USB → .img (NOT network clone from a live Pi).
set -euo pipefail

DEV="${1:-/dev/sdc}"
OUT="${2:-$HOME/rio-scenario1-bullseye.img}"

if [[ ! -b "$DEV" ]]; then
  echo "ERROR: $DEV not found. Plug the SD into the CoolerMaster USB reader." >&2
  exit 1
fi

TRAN=$(lsblk -no TRAN "$DEV" | head -1 | tr -d '[:space:]')
SIZE_B=$(lsblk -bno SIZE "$DEV" | head -1 | tr -d '[:space:]')
SIZE_G=$((SIZE_B / 1000000000))
LABELS=$(lsblk -no LABEL "$DEV" | tr '\n' ' ')

echo "Source: $DEV  tran=$TRAN  size≈${SIZE_G}G  labels=[$LABELS]"
echo "Output: $OUT"

if [[ "$TRAN" != "usb" ]]; then
  echo "ERROR: refusing non-USB device (tran=$TRAN)" >&2
  exit 1
fi
if [[ "$SIZE_G" -lt 20 || "$SIZE_G" -gt 40 ]]; then
  echo "ERROR: unexpected size ${SIZE_G}G (expected ~30G microSD)" >&2
  exit 1
fi

# Unmount any automounted partitions
sudo umount "${DEV}"?* 2>/dev/null || true
sync

# Only copy through end of last partition (skip unused trailing space) → ~7GB not 30GB
END_SECTOR=$(sudo fdisk -l "$DEV" | awk '/^\/dev\//{print $3}' | sort -n | tail -1)
if [[ -z "$END_SECTOR" ]]; then
  echo "ERROR: could not read partition table on $DEV" >&2
  exit 1
fi
# sectors are 512 bytes; convert to 4MiB blocks (ceil)
BYTES=$(( (END_SECTOR + 1) * 512 ))
BLOCKS=$(( (BYTES + 4194303) / 4194304 ))
echo "Copying $BLOCKS × 4MiB (~$((BLOCKS*4)) MiB) through sector $END_SECTOR ..."

sudo dd if="$DEV" of="$OUT" bs=4M count="$BLOCKS" status=progress conv=fsync
sudo sync
sudo chown "${SUDO_USER:-$USER}:${SUDO_USER:-$USER}" "$OUT" 2>/dev/null || true

echo
echo "OK: $(ls -lh "$OUT" | awk '{print $5, $9}')"
echo "Partition table in image:"
fdisk -l "$OUT" | tail -8
echo
echo "To flash another SD later:"
echo "  sudo $(dirname "$0")/write-rio-sd.sh $OUT /dev/sdX"
