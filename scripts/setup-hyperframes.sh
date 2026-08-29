#!/usr/bin/env bash
# Bring a container up to the point where `hyperframes render` produces an MP4.
#
# HyperFrames renders by driving headless Chrome frame by frame and encoding the
# frames with FFmpeg. A fresh container has neither. This installs both, then
# asks the CLI to confirm.
#
# Safe to re-run: apt and `browser ensure` both no-op once satisfied.

set -euo pipefail

HF="${HYPERFRAMES_VERSION:-latest}"

echo "==> FFmpeg + FFprobe"
if command -v ffmpeg >/dev/null && command -v ffprobe >/dev/null; then
  echo "    already present: $(ffmpeg -version | head -1)"
else
  if [ "$(id -u)" -ne 0 ] && ! command -v sudo >/dev/null; then
    echo "    need root or sudo to install ffmpeg" >&2
    exit 1
  fi
  SUDO=""
  [ "$(id -u)" -ne 0 ] && SUDO="sudo"
  # Third-party PPAs may be blocked by an egress policy; the main archive is
  # enough for ffmpeg, so a failed update must not abort the install.
  $SUDO apt-get update -qq || true
  $SUDO env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ffmpeg
fi

echo "==> Chrome Headless Shell"
npx --yes "hyperframes@${HF}" browser ensure

echo "==> Verifying"
# doctor exits non-zero while any optional check is unmet (whisper, Kokoro,
# Docker...), so gate on the three that actually decide whether a render runs.
report="$(npx --yes "hyperframes@${HF}" doctor 2>&1 || true)"
echo "$report"

missing=""
for dep in FFmpeg FFprobe Chrome; do
  grep -q "✓ $dep" <<<"$report" || missing="$missing $dep"
done

if [ -n "$missing" ]; then
  echo
  echo "Cannot render — still missing:$missing" >&2
  exit 1
fi

echo
echo "Ready to render. Optional checks above (whisper, Kokoro, MusicGen, Docker)"
echo "are not needed for a plain MP4."
