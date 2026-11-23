#!/usr/bin/env bash
set -euo pipefail

root="${1:-.}"

if ! command -v magick >/dev/null 2>&1; then
  echo "ImageMagick is required (the 'magick' command was not found)." >&2
  exit 1
fi

find "$root" -type f \
  \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.webp' \) \
  -print0 | xargs -0 -r magick mogrify -strip

echo "Removed embedded EXIF, IPTC, XMP, comments, profiles, and location metadata from images under $root."
