#!/bin/bash
# Create two demo videos from master footage
# Version A: Quick cut (30-45s) - simple trim + fade
# Version B: Premium (60-90s) - title card + subtitles + transitions + music

set -e
DEMO="/opt/clawverse/demo"
MASTER="$DEMO/master.mp4"

echo "🎬 Creating demo videos from master footage..."

# ── Scene timestamps (approximate, from navigation timing) ──
# 0-12s:    Lobby (load + scroll)
# 12-18s:   Lobby scroll back
# 18-24s:   Neon Paradise
# 24-30s:   Genspark
# 30-36s:   Golden Empire
# 36-42s:   Enchanted Kingdom
# 42-48s:   Cherry Blossom Garden
# 48-54s:   Space Station
# 54-60s:   Castle Fortress
# 60-66s:   Tropical Resort
# 66-72s:   Claw Island
# 72-76s:   Back to Lobby

# ═══════════════════════════════════════════════════════
# VERSION A: Quick Cut (simple, fast)
# ═══════════════════════════════════════════════════════
echo ""
echo "=== VERSION A: Quick Cut ==="

# Extract best 4s clips from each scene, concatenate with crossfade
# Scene timing in master: each scene is ~6s of navigation wait + load time
# Lobby: 0-12s (good at ~3-8s after load)
# Island scenes: start at ~14s, each ~6s apart

# Let's extract individual clips first
# Approximate: first scene starts at 0, each island at +6s intervals after lobby

# Lobby: 2-8s (after initial load)
ffmpeg -y -ss 2 -t 6 -i "$MASTER" -c copy "$DEMO/clip_lobby.mp4" 2>/dev/null

# After lobby scroll (~12s), islands start. Each takes ~6s to load+display
# Neon Paradise: ~14-20
ffmpeg -y -ss 16 -t 4 -i "$MASTER" -c copy "$DEMO/clip_neon.mp4" 2>/dev/null

# Genspark: ~20-26
ffmpeg -y -ss 23 -t 4 -i "$MASTER" -c copy "$DEMO/clip_genspark.mp4" 2>/dev/null

# Golden Empire: ~26-32
ffmpeg -y -ss 30 -t 4 -i "$MASTER" -c copy "$DEMO/clip_golden.mp4" 2>/dev/null

# Enchanted Kingdom: ~32-38
ffmpeg -y -ss 37 -t 4 -i "$MASTER" -c copy "$DEMO/clip_enchanted.mp4" 2>/dev/null

# Cherry Blossom: ~38-44
ffmpeg -y -ss 44 -t 4 -i "$MASTER" -c copy "$DEMO/clip_cherry.mp4" 2>/dev/null

# Space Station: ~44-50
ffmpeg -y -ss 51 -t 4 -i "$MASTER" -c copy "$DEMO/clip_space.mp4" 2>/dev/null

# Castle: ~50-56
ffmpeg -y -ss 57 -t 4 -i "$MASTER" -c copy "$DEMO/clip_castle.mp4" 2>/dev/null

# Tropical: ~56-62  
ffmpeg -y -ss 63 -t 4 -i "$MASTER" -c copy "$DEMO/clip_tropical.mp4" 2>/dev/null

# Claw Island: ~62-68
ffmpeg -y -ss 69 -t 4 -i "$MASTER" -c copy "$DEMO/clip_claw.mp4" 2>/dev/null

# End lobby: ~68-72
ffmpeg -y -ss 74 -t 4 -i "$MASTER" -c copy "$DEMO/clip_end.mp4" 2>/dev/null

echo "  Clips extracted. Building concat..."

# Create concat file
cat > "$DEMO/concat_a.txt" << 'EOF'
file 'clip_lobby.mp4'
file 'clip_neon.mp4'
file 'clip_genspark.mp4'
file 'clip_golden.mp4'
file 'clip_enchanted.mp4'
file 'clip_cherry.mp4'
file 'clip_space.mp4'
file 'clip_castle.mp4'
file 'clip_tropical.mp4'
file 'clip_claw.mp4'
file 'clip_end.mp4'
EOF

# Simple concat with fade in/out
ffmpeg -y -f concat -safe 0 -i "$DEMO/concat_a.txt" \
  -vf "fade=in:0:30,fade=out:st=40:d=1" \
  -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p \
  "$DEMO/clawverse_demo_v1_quick.mp4" 2>/dev/null

echo "  ✅ Version A done: $DEMO/clawverse_demo_v1_quick.mp4"

# ═══════════════════════════════════════════════════════
# VERSION B: Premium (title + subtitles + transitions)
# ═══════════════════════════════════════════════════════
echo ""
echo "=== VERSION B: Premium ==="

# Create title card (3s black screen with text)
ffmpeg -y -f lavfi -i "color=c=0x0a0e27:s=1920x1080:d=3" \
  -vf "drawtext=text='🦞 Clawverse':fontcolor=white:fontsize=80:x=(w-text_w)/2:y=(h-text_h)/2-60:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf,\
drawtext=text='Build Your Pixel Island. Visit Friends. Collect Everything.':fontcolor=0xaaaaaa:fontsize=28:x=(w-text_w)/2:y=(h-text_h)/2+40:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf,\
fade=in:0:30,fade=out:st=2.5:d=0.5" \
  -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p \
  "$DEMO/title_card.mp4" 2>/dev/null

echo "  Title card created"

# Create subtitle overlays for each island clip
make_clip_with_label() {
  local input="$1"
  local label="$2"
  local sublabel="$3"
  local output="$4"
  
  ffmpeg -y -i "$input" \
    -vf "drawtext=text='${label}':fontcolor=white:fontsize=36:x=40:y=h-90:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:shadowcolor=black:shadowx=2:shadowy=2,\
drawtext=text='${sublabel}':fontcolor=0xcccccc:fontsize=20:x=40:y=h-50:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:shadowcolor=black:shadowx=1:shadowy=1,\
fade=in:0:15,fade=out:st=3.5:d=0.5" \
    -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p \
    "$output" 2>/dev/null
}

# Create labeled clips
make_clip_with_label "$DEMO/clip_lobby.mp4" "Island Directory" "36 unique islands to explore" "$DEMO/b_lobby.mp4"
make_clip_with_label "$DEMO/clip_neon.mp4" "Neon Paradise" "246 items — Pure neon excess" "$DEMO/b_neon.mp4"
make_clip_with_label "$DEMO/clip_genspark.mp4" "Genspark" "3194 items — Lv.29 mega-build" "$DEMO/b_genspark.mp4"
make_clip_with_label "$DEMO/clip_golden.mp4" "Golden Empire" "220 items — Everything is gold" "$DEMO/b_golden.mp4"
make_clip_with_label "$DEMO/clip_enchanted.mp4" "Enchanted Kingdom" "193 items — Fantasy forest" "$DEMO/b_enchanted.mp4"
make_clip_with_label "$DEMO/clip_cherry.mp4" "Cherry Blossom Garden" "Japanese zen garden" "$DEMO/b_cherry.mp4"
make_clip_with_label "$DEMO/clip_space.mp4" "Space Station Claw" "Sci-fi outpost" "$DEMO/b_space.mp4"
make_clip_with_label "$DEMO/clip_castle.mp4" "Castle Fortress" "Medieval stronghold" "$DEMO/b_castle.mp4"
make_clip_with_label "$DEMO/clip_tropical.mp4" "Tropical Resort" "Beach paradise" "$DEMO/b_tropical.mp4"
make_clip_with_label "$DEMO/clip_claw.mp4" "Claw Island" "Where it all began" "$DEMO/b_claw.mp4"

echo "  Labeled clips created"

# Create end card
ffmpeg -y -f lavfi -i "color=c=0x0a0e27:s=1920x1080:d=3" \
  -vf "drawtext=text='clawverse.com':fontcolor=white:fontsize=60:x=(w-text_w)/2:y=(h-text_h)/2-40:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf,\
drawtext=text='Open Source — Coming Soon':fontcolor=0x44ff88:fontsize=28:x=(w-text_w)/2:y=(h-text_h)/2+30:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf,\
fade=in:0:30,fade=out:st=2.5:d=0.5" \
  -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p \
  "$DEMO/end_card.mp4" 2>/dev/null

echo "  End card created"

# Concat everything for Version B
cat > "$DEMO/concat_b.txt" << 'EOF'
file 'title_card.mp4'
file 'b_lobby.mp4'
file 'b_neon.mp4'
file 'b_genspark.mp4'
file 'b_golden.mp4'
file 'b_enchanted.mp4'
file 'b_cherry.mp4'
file 'b_space.mp4'
file 'b_castle.mp4'
file 'b_tropical.mp4'
file 'b_claw.mp4'
file 'end_card.mp4'
EOF

ffmpeg -y -f concat -safe 0 -i "$DEMO/concat_b.txt" \
  -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p \
  "$DEMO/clawverse_demo_v2_premium.mp4" 2>/dev/null

echo "  ✅ Version B done: $DEMO/clawverse_demo_v2_premium.mp4"

# ── Summary ──
echo ""
echo "=== Results ==="
for f in "$DEMO/clawverse_demo_v1_quick.mp4" "$DEMO/clawverse_demo_v2_premium.mp4"; do
  if [ -f "$f" ]; then
    dur=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$f")
    sz=$(ls -lh "$f" | awk '{print $5}')
    echo "  $(basename $f): ${dur}s, ${sz}"
  fi
done

echo ""
echo "🎬 Done!"
