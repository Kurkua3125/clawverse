#!/bin/bash
# Build the FINAL viral demo video
# Strategy: 
# - Open with WOW (most spectacular island, no title card)
# - Fast snap cuts (2-2.5s each)
# - Ken Burns alternating directions
# - Labels at bottom
# - End with CTA
# Total: ~30s (Twitter optimal)

set -e
D="/opt/clawverse/demo/final_assets"
OUT="/opt/clawverse/demo/final_video"
mkdir -p "$OUT"

echo "🎬 Building FINAL viral demo video"

# Function: create clip with Ken Burns + bottom label
make_clip() {
  local img="$1" dur="$2" label="$3" sub="$4" zoom_dir="$5" out="$6"
  
  local zoom_expr
  case "$zoom_dir" in
    in)  zoom_expr="z='min(zoom+0.0004,1.04)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'" ;;
    out) zoom_expr="z='if(eq(on,1),1.04,max(zoom-0.0004,1.0))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'" ;;
    left) zoom_expr="z=1.03:x='iw*0.015+iw*0.015*on/(${dur}*30)':y='ih/2-(ih/zoom/2)'" ;;
    right) zoom_expr="z=1.03:x='iw*0.03-iw*0.015*on/(${dur}*30)':y='ih/2-(ih/zoom/2)'" ;;
  esac
  
  local vf="scale=2048:1152,crop=1920:1080,zoompan=${zoom_expr}:d=$((dur*30)):s=1920x1080:fps=30"
  
  # Add label bar
  if [ -n "$label" ]; then
    vf="${vf},drawbox=x=0:y=ih-70:w=iw:h=70:color=black@0.55:t=fill"
    vf="${vf},drawtext=text='${label}':fontcolor=white:fontsize=28:x=35:y=h-52:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    if [ -n "$sub" ]; then
      vf="${vf},drawtext=text='${sub}':fontcolor=0xbbbbbb:fontsize=16:x=35:y=h-22:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    fi
  fi
  
  ffmpeg -y -loop 1 -i "$img" -vf "$vf" -t "$dur" \
    -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p "$out" 2>/dev/null
  
  [ -f "$out" ] && echo "  ✅ $(basename $out)" || echo "  ❌ $(basename $out)"
}

# ── Build all clips ──
echo ""
echo "=== Building clips ==="

# Use the browser neon screenshot as the opener (best quality)
make_clip "$D/neon_browser.jpg" 3 "Neon Paradise" "246 items — Built by AI" "in" "$OUT/01.mp4"
make_clip "$D/genspark.jpg" 2 "Genspark" "3,194 items — Lv.29" "out" "$OUT/02.mp4"
make_clip "$D/golden.jpg" 2 "Golden Empire" "220 items" "left" "$OUT/03.mp4"
make_clip "$D/enchanted.jpg" 2 "Enchanted Kingdom" "Fantasy forest" "right" "$OUT/04.mp4"
make_clip "$D/cherry.jpg" 2 "Cherry Blossom Garden" "Japanese zen" "in" "$OUT/05.mp4"
make_clip "$D/space.jpg" 2 "Space Station Claw" "Sci-fi outpost" "out" "$OUT/06.mp4"
make_clip "$D/castle.jpg" 2 "Castle Fortress" "Medieval realm" "left" "$OUT/07.mp4"
make_clip "$D/tropical.jpg" 2 "Tropical Resort" "Beach paradise" "right" "$OUT/08.mp4"
make_clip "$D/claw.jpg" 3 "Claw Island" "Where it all began" "in" "$OUT/09.mp4"

# End CTA card (3s)
ffmpeg -y -f lavfi -i "color=c=0x0a0e27:s=1920x1080:d=3" \
  -vf "drawtext=text='Build your island':fontcolor=white:fontsize=72:x=(w-text_w)/2:y=(h-text_h)/2-50:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf,\
drawtext=text='clawverse.com':fontcolor=0x44ff88:fontsize=36:x=(w-text_w)/2:y=(h-text_h)/2+30:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf,\
drawtext=text='Open Source — Play Now':fontcolor=0x888888:fontsize=22:x=(w-text_w)/2:y=(h-text_h)/2+75:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf" \
  -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p "$OUT/10_cta.mp4" 2>/dev/null
echo "  ✅ CTA card"

# ── Assemble ──
echo ""
echo "=== Assembling ==="
cat > "$OUT/concat.txt" << 'EOF'
file '01.mp4'
file '02.mp4'
file '03.mp4'
file '04.mp4'
file '05.mp4'
file '06.mp4'
file '07.mp4'
file '08.mp4'
file '09.mp4'
file '10_cta.mp4'
EOF

FINAL="$OUT/clawverse_viral.mp4"
ffmpeg -y -f concat -safe 0 -i "$OUT/concat.txt" \
  -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p "$FINAL" 2>/dev/null

dur=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$FINAL" 2>/dev/null)
sz=$(ls -lh "$FINAL" | awk '{print $5}')
echo ""
echo "🎬 FINAL: ${dur}s, ${sz}, 1920x1080"
echo "   File: $FINAL"

# ── Also analyze with video model ──
echo ""
echo "=== Self-analysis ==="
