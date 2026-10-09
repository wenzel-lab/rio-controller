#!/bin/bash
# Deploy the Scenario 1 (Raspberry Pi Camera + strobe) Rio stack onto an SD card
# that is plugged into this PC (Raspbian rootfs/bootfs auto-mounted under /media).
#
# Usage:  rio-sd-deploy [--eject] [--no-build]
#   --eject     unmount + power-off the card when done (safe to pull)
#   --no-build  skip regenerating pi-deployment/ from software/
#
# Runs as root via sudoers (/etc/sudoers.d/rio-sd-deploy, NOPASSWD for this path);
# pi-deployment/ is regenerated as the invoking user so the repo stays user-owned.
#
# What it installs on the card (same click path that has worked for years):
#   /home/pi/rio-controller/                    rsync of pi-deployment/ (code + icons)
#   /etc/systemd/system/rio-ui.service          backend on :5000 at boot (+ enable symlink)
#   ~pi/Desktop/chrome-<app-id>-Default.desktop Chromium PWA shortcut (original app-id)
#   ~pi/.local/share/applications/…             same shortcut for the menu
#   ~pi/.config/autostart/omw.desktop           fallback: run.sh if :5000 is down
#   hicolor + Chromium manifest icons           new Rio logo
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
APP_ID="fimaojahdaklnkiolkpkkdpagifaifll"

EJECT=0
BUILD=1
for arg in "$@"; do
    case "$arg" in
        --eject) EJECT=1 ;;
        --no-build) BUILD=0 ;;
        -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
        *) echo "Unknown option: $arg" >&2; exit 2 ;;
    esac
done

if [ "$(id -u)" -ne 0 ]; then
    exec sudo -n "$0" "$@"
fi
DEPLOY_USER="${SUDO_USER:-$(logname 2>/dev/null || echo tobias-wenzel)}"

run_as_user() {
    if [ -n "${SUDO_USER:-}" ]; then
        sudo -u "$SUDO_USER" -- "$@"
    else
        "$@"
    fi
}

# --- locate the card -------------------------------------------------------
find_mount_by_label() {
    # Prefer a real, non-empty mountpoint for the given filesystem LABEL.
    lsblk -nr -o LABEL,MOUNTPOINT | awk -v l="$1" '$1==l && $2!="" {print $2; exit}'
}
ROOT_MNT="$(find_mount_by_label rootfs || true)"
BOOT_MNT="$(find_mount_by_label bootfs || true)"
if [ -z "$ROOT_MNT" ] || [ ! -d "$ROOT_MNT/home/pi" ]; then
    echo "ERROR: Raspbian rootfs not mounted (insert the SD and wait for auto-mount)." >&2
    lsblk -o NAME,LABEL,MOUNTPOINT,SIZE,RM | grep -E "rootfs|bootfs|^sd" || true
    exit 1
fi
ROOT_DEV="$(lsblk -nr -o PATH,MOUNTPOINT | awk -v m="$ROOT_MNT" '$2==m {print $1; exit}')"
DISK_DEV="/dev/$(lsblk -nr -o PKNAME "$ROOT_DEV" | head -1)"
echo "Card rootfs: $ROOT_MNT ($ROOT_DEV on $DISK_DEV)  bootfs: ${BOOT_MNT:-n/a}"

PI_HOME="$ROOT_MNT/home/pi"
DEST="$PI_HOME/rio-controller"

# --- build pi-deployment/ as the normal user --------------------------------
if [ "$BUILD" -eq 1 ]; then
    echo "=== create-pi-deployment (as $DEPLOY_USER) ==="
    run_as_user bash "$REPO_ROOT/scripts/deploy/create-pi-deployment.sh" >/dev/null
fi
SRC="$REPO_ROOT/pi-deployment"
[ -f "$SRC/main.py" ] || { echo "ERROR: $SRC/main.py missing" >&2; exit 1; }

# --- code ----------------------------------------------------------------------
echo "=== rsync pi-deployment → $DEST ==="
mkdir -p "$DEST"
rsync -a --exclude '__pycache__' --exclude '*.pyc' "$SRC/" "$DEST/"
touch "$DEST/rio-ui.log"
chmod +x "$DEST/run.sh" 2>/dev/null || true
chown -R 1000:1000 "$DEST"

# --- systemd service (backend on :5000 at boot) --------------------------------
echo "=== systemd rio-ui.service ==="
install -m 644 "$REPO_ROOT/scripts/pi/systemd/rio-ui.service" "$ROOT_MNT/etc/systemd/system/rio-ui.service"
mkdir -p "$ROOT_MNT/etc/systemd/system/multi-user.target.wants"
ln -sf /etc/systemd/system/rio-ui.service "$ROOT_MNT/etc/systemd/system/multi-user.target.wants/rio-ui.service"

# --- desktop shortcut (original Chromium PWA app-id) + autostart fallback ------
echo "=== Desktop + autostart ==="
DESKTOP_SRC="$SRC/rio-webapp/omw.desktop"
AUTOSTART_SRC="$SRC/rio-webapp/omw-autostart.desktop"
mkdir -p "$PI_HOME/Desktop" "$PI_HOME/.local/share/applications" "$PI_HOME/.config/autostart"
install -m 755 "$DESKTOP_SRC" "$PI_HOME/Desktop/chrome-${APP_ID}-Default.desktop"
install -m 644 "$DESKTOP_SRC" "$PI_HOME/.local/share/applications/chrome-${APP_ID}-Default.desktop"
install -m 644 "$AUTOSTART_SRC" "$PI_HOME/.config/autostart/omw.desktop"
# leftovers from abandoned launcher experiments
rm -f "$PI_HOME/Desktop/Rio-Controller.desktop" "$PI_HOME/Desktop/launch-rio.sh" \
      "$PI_HOME/.local/share/applications/Rio-Controller.desktop"

# --- icons -----------------------------------------------------------------------
echo "=== icons ==="
ICONS="$SRC/rio-webapp/static/icons"
for s in 32 48 64 128 256; do
    d="$PI_HOME/.local/share/icons/hicolor/${s}x${s}/apps"
    mkdir -p "$d"
    install -m 644 "$ICONS/rio-logo-$s.png" "$d/chrome-${APP_ID}-Default.png"
done
MANIFEST_ICONS="$PI_HOME/.config/chromium/Default/Web Applications/Manifest Resources/$APP_ID/Icons"
if [ -d "$MANIFEST_ICONS" ]; then
    for s in 32 48 64 96 128 256; do
        [ -f "$ICONS/rio-logo-$s.png" ] && install -m 644 "$ICONS/rio-logo-$s.png" "$MANIFEST_ICONS/$s.png"
    done
fi
chown -R 1000:1000 "$PI_HOME/Desktop" "$PI_HOME/.local/share/applications" \
    "$PI_HOME/.local/share/icons" "$PI_HOME/.config/autostart" "$MANIFEST_ICONS" 2>/dev/null || true

# --- verify --------------------------------------------------------------------------
echo "=== verify ==="
fail=0
chk() { if eval "$2"; then echo "$1: OK"; else echo "$1: FAIL"; fail=1; fi; }
chk "PTS module"      "[ -f '$DEST/drivers/camera/h264_timestamped_output.py' ]"
chk "HTTP cam API"    "grep -q 'api/camera/snapshot' '$DEST/rio-webapp/routes.py' && grep -q 'api/camera/roi' '$DEST/rio-webapp/routes.py'"
chk "UI uses HTTP"    "grep -q \"camPost('/api/camera/snapshot'\" '$DEST/rio-webapp/templates/index.html' && grep -q '/api/camera/roi' '$DEST/rio-webapp/templates/index.html'"
chk "socket.io local" "[ -f '$DEST/rio-webapp/static/vendor/socket.io.min.js' ]"
chk "NO_GEVENT"       "grep -q 'RIO_NO_GEVENT_PATCH=true' '$ROOT_MNT/etc/systemd/system/rio-ui.service'"
chk "SYSTEMD boot"    "[ -L '$ROOT_MNT/etc/systemd/system/multi-user.target.wants/rio-ui.service' ]"
chk "DESKTOP app-id"  "grep -q -- '--app-id=$APP_ID' '$PI_HOME/Desktop/chrome-${APP_ID}-Default.desktop'"
chk "ICON"            "[ -f '$DEST/rio-webapp/static/icons/rio-controller.png' ]"
echo "Desktop Exec: $(grep '^Exec=' "$PI_HOME/Desktop/chrome-${APP_ID}-Default.desktop")"

sync
echo "sync done"
[ "$fail" -eq 0 ] || { echo "VERIFY FAILED — card NOT ejected" >&2; exit 1; }

# --- eject -------------------------------------------------------------------------
if [ "$EJECT" -eq 1 ]; then
    echo "=== eject ==="
    for p in $(lsblk -nr -o PATH,MOUNTPOINT "$DISK_DEV" | awk '$2!="" {print $1}'); do
        umount "$p" || { echo "umount $p failed" >&2; exit 1; }
    done
    udisksctl power-off -b "$DISK_DEV" >/dev/null 2>&1 || true
    echo "EJECT_OK — safe to remove the SD"
fi
