#!/bin/bash
# Rapidly capture all island screenshots using the browser tool's screenshot files
# The browser tool saves screenshots to /home/azureuser/.openclaw/media/browser/
# We navigate, wait, screenshot, and copy

DEMO="/opt/clawverse/demo/viral"
MEDIA="/home/azureuser/.openclaw/media/browser"
BASE="https://ysnlpjle.gensparkclaw.com"

echo "🎬 Rapid screenshot capture"

# We'll use the last file in the media dir after each screenshot
get_latest() {
  ls -t "$MEDIA"/*.png "$MEDIA"/*.jpg 2>/dev/null | head -1
}

# For each island, we already have good CDP screenshots in demo/pro/
# Let's upscale those to 1920x1080 since they're already loaded content

echo "Upscaling existing CDP screenshots..."
for name in neon genspark golden enchanted cherry castle space tropical claw; do
  src="$DEMO/../pro/ss_${name}.jpg"
  dst="$DEMO/${name}_hd.jpg"
  if [ -f "$src" ]; then
    ffmpeg -y -i "$src" -vf "scale=1920:1080:flags=lanczos" "$dst" 2>/dev/null
    sz=$(ls -lh "$dst" | awk '{print $5}')
    echo "  ✅ $name ($sz)"
  fi
done

echo "Done!"
