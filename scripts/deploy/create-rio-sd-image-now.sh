#!/bin/bash
# Non-interactive: create Rio Scenario-1 .img from USB SD (/dev/sdc).
# Run in a normal CoolerMaster terminal (needs your sudo password once):
#   bash ~/rio-controller/scripts/deploy/create-rio-sd-image-now.sh
set -euo pipefail

DEV=/dev/sdc
OUT="$HOME/rio-scenario1-bullseye.img"

[[ -b "$DEV" ]] || { echo "ERROR: $DEV missing — is the SD plugged in?"; exit 1; }
TRAN=$(lsblk -no TRAN "$DEV" | head -1 | tr -d '[:space:]')
[[ "$TRAN" == "usb" ]] || { echo "ERROR: $DEV is not USB (tran=$TRAN)"; exit 1; }

echo "=== Source ==="
lsblk -o NAME,SIZE,FSTYPE,LABEL,TRAN "$DEV"
echo
echo "=== Unmounting ==="
sudo umount "${DEV}"?* 2>/dev/null || true
sync

END_SECTOR=$(sudo fdisk -l "$DEV" | awk '/^\/dev\//{end=$3} END{print end}')
BYTES=$(( (END_SECTOR + 1) * 512 ))
BLOCKS=$(( (BYTES + 4194303) / 4194304 ))
echo "Copying ~$((BLOCKS*4)) MiB (through sector $END_SECTOR) → $OUT"
echo "(USB local — should be minutes, not an hour)"
echo

sudo dd if="$DEV" of="$OUT" bs=4M count="$BLOCKS" status=progress conv=fsync
sudo sync
sudo chown "$USER:$USER" "$OUT"

echo
echo "=== DONE ==="
ls -lh "$OUT"
fdisk -l "$OUT" | tail -8
echo
echo "Image ready: $OUT"
echo "Flash another card with:"
echo "  sudo $HOME/rio-controller/scripts/deploy/write-rio-sd.sh $OUT /dev/sdX"
