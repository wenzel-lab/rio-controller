#!/bin/bash
# Write Rio Scenario 1 image to the microSD in the CoolerMaster USB reader.
# SAFETY: only writes to /dev/sdc if it is a ~30GB USB disk labeled Mass-Storage.
set -euo pipefail

IMG="${1:-/home/tobias-wenzel/rio-scenario1-bullseye.img}"
DEV="${2:-/dev/sdc}"

if [[ ! -f "$IMG" ]]; then
  echo "ERROR: image not found: $IMG" >&2
  exit 1
fi
if [[ ! -b "$DEV" ]]; then
  echo "ERROR: block device not found: $DEV" >&2
  exit 1
fi

# Refuse to touch internal NVMe / huge SATA disks
TRAN=$(lsblk -no TRAN "$DEV" 2>/dev/null | head -1 | tr -d ' ')
SIZE_G=$(lsblk -bno SIZE "$DEV" | awk '{printf "%.0f", $1/1e9}')
MODEL=$(lsblk -no MODEL "$DEV" | head -1 | xargs)

echo "Target: $DEV  tran=$TRAN  size≈${SIZE_G}G  model='$MODEL'"
echo "Image:  $IMG ($(du -h "$IMG" | awk 'NR==1{print $1}'))"

if [[ "$TRAN" != "usb" ]]; then
  echo "ERROR: refusing non-USB device (tran=$TRAN)" >&2
  exit 1
fi
if [[ "$SIZE_G" -lt 20 || "$SIZE_G" -gt 40 ]]; then
  echo "ERROR: refusing unexpected size ${SIZE_G}G (expected ~30G SD)" >&2
  exit 1
fi

read -r -p "Type YES to ERASE $DEV and write the Rio image: " ans
[[ "$ans" == "YES" ]] || { echo "Aborted."; exit 1; }

sudo umount "${DEV}"* 2>/dev/null || true
sudo dd if="$IMG" of="$DEV" bs=4M status=progress conv=fsync
sudo sync
echo "Done. Verify:"
sudo fdisk -l "$DEV" | tail -12
lsblk -o NAME,SIZE,FSTYPE,LABEL "$DEV"
echo "You can eject the SD and boot the new Pi."
