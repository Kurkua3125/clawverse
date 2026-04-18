#!/bin/bash
set -e
D="/opt/clawverse/demo/pro"

echo "🎬 Making Version 3 (Showcase Reel, 30s) and Version 4 (Cinematic Tour, 60s)"

# ════════════════════════════════════════════════════
# VERSION 3: Showcase Reel — 30s, fast cuts, bold text
# ════════════════════════════════════════════════════
echo ""
echo "=== VERSION 3: Showcase Reel (30s) ==="

# Title card (2s)
ffmpeg -y -f lavfi -i "color=c=0x0a0e27:s=1920x1080:d=2" \
  -vf "drawtext=text='CLAWVERSE':fontcolor=white:fontsize=96:x=(w-text_w)/2:y=(h-text_h)/2-40:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf,\
drawtext=text='Build. Visit. Collect.':fontcolor=0x44ddff:fontsize=36:x=(w-text_w)/2:y=(h-text_h)/2+50:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf,\
fade=in:0:15,fade=out:st=1.5:d=0.5" \
  -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p "$D/v3_title.mp4" 2>/dev/null
echo "  ✅ Title"

# Function: short punchy clip from screenshot
make_punch() {
  local img="$1" label="$2" out="$3"
  ffmpeg -y -loop 1 -i "$img" \
    -vf "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,\
zoompan=z='min(zoom+0.0005,1.04)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=75:s=1920x1080:fps=30,\
drawbox=x=0:y=ih-70:w=iw:h=70:color=black@0.6:t=fill,\
drawtext=text='${label}':fontcolor=white:fontsize=36:x=30:y=h-52:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf,\
fade=in:0:10,fade=out:st=2:d=0.5" \
    -t 2.5 -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p "$out" 2>/dev/null
}

make_punch "$D/ss_lobby.jpg" "36 Islands to Explore" "$D/v3_lobby.mp4" && echo "  ✅ lobby"
make_punch "$D/ss_neon.jpg" "Neon Paradise" "$D/v3_neon.mp4" && echo "  ✅ neon"
make_punch "$D/ss_genspark.jpg" "Genspark — 3,194 items" "$D/v3_genspark.mp4" && echo "  ✅ genspark"
make_punch "$D/ss_golden.jpg" "Golden Empire" "$D/v3_golden.mp4" && echo "  ✅ golden"
make_punch "$D/ss_enchanted.jpg" "Enchanted Kingdom" "$D/v3_enchanted.mp4" && echo "  ✅ enchanted"
make_punch "$D/ss_cherry.jpg" "Cherry Blossom Garden" "$D/v3_cherry.mp4" && echo "  ✅ cherry"
make_punch "$D/ss_space.jpg" "Space Station" "$D/v3_space.mp4" && echo "  ✅ space"
make_punch "$D/ss_castle.jpg" "Castle Fortress" "$D/v3_castle.mp4" && echo "  ✅ castle"
make_punch "$D/ss_tropical.jpg" "Tropical Resort" "$D/v3_tropical.mp4" && echo "  ✅ tropical"
make_punch "$D/ss_claw.jpg" "Claw Island" "$D/v3_claw.mp4" && echo "  ✅ claw"

# End card (2s)
ffmpeg -y -f lavfi -i "color=c=0x0a0e27:s=1920x1080:d=2" \
  -vf "drawtext=text='Try it free':fontcolor=0x44ff88:fontsize=64:x=(w-text_w)/2:y=(h-text_h)/2-30:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf,\
drawtext=text='clawverse.com':fontcolor=white:fontsize=36:x=(w-text_w)/2:y=(h-text_h)/2+40:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf,\
fade=in:0:15,fade=out:st=1.5:d=0.5" \
  -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p "$D/v3_end.mp4" 2>/dev/null
echo "  ✅ End card"

# Concat V3
cat > "$D/v3_concat.txt" << 'EOF'
file 'v3_title.mp4'
file 'v3_lobby.mp4'
file 'v3_neon.mp4'
file 'v3_genspark.mp4'
file 'v3_golden.mp4'
file 'v3_enchanted.mp4'
file 'v3_cherry.mp4'
file 'v3_space.mp4'
file 'v3_castle.mp4'
file 'v3_tropical.mp4'
file 'v3_claw.mp4'
file 'v3_end.mp4'
EOF

ffmpeg -y -f concat -safe 0 -i "$D/v3_concat.txt" \
  -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p \
  "$D/clawverse_v3_showcase.mp4" 2>/dev/null

V3DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$D/clawverse_v3_showcase.mp4")
V3SZ=$(ls -lh "$D/clawverse_v3_showcase.mp4" | awk '{print $5}')
echo "  🎬 V3 DONE: ${V3DUR}s, ${V3SZ}"

# ════════════════════════════════════════════════════
# VERSION 4: Cinematic Tour — 60s, smooth, xfade
# ════════════════════════════════════════════════════
echo ""
echo "=== VERSION 4: Cinematic Tour (60s) ==="

# Build individual 5s clips with Ken Burns and labels
make_cinema() {
  local img="$1" label="$2" sub="$3" out="$4"
  ffmpeg -y -loop 1 -i "$img" \
    -vf "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,\
zoompan=z='min(zoom+0.0002,1.02)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=150:s=1920x1080:fps=30,\
drawbox=x=0:y=ih-85:w=iw:h=85:color=black@0.45:t=fill,\
drawtext=text='${label}':fontcolor=white:fontsize=30:x=40:y=h-68:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf,\
drawtext=text='${sub}':fontcolor=0xbbbbbb:fontsize=18:x=40:y=h-32:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf,\
fade=in:0:15,fade=out:st=4.3:d=0.7" \
    -t 5 -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p "$out" 2>/dev/null
}

# Title (3s)
ffmpeg -y -f lavfi -i "color=c=0x0a0e27:s=1920x1080:d=3" \
  -vf "drawtext=text='Clawverse':fontcolor=white:fontsize=80:x=(w-text_w)/2:y=(h-text_h)/2-60:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf,\
drawtext=text='Build Your Pixel Island':fontcolor=0x66ccff:fontsize=32:x=(w-text_w)/2:y=(h-text_h)/2+20:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf,\
drawtext=text='Visit Friends. Collect Everything.':fontcolor=0x888888:fontsize=24:x=(w-text_w)/2:y=(h-text_h)/2+60:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf,\
fade=in:0:25,fade=out:st=2.3:d=0.7" \
  -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p "$D/v4_title.mp4" 2>/dev/null
echo "  ✅ Title"

make_cinema "$D/ss_lobby.jpg" "Island Directory" "36 unique islands — farms, fisheries, mines, forests" "$D/v4_lobby.mp4" && echo "  ✅ lobby"
make_cinema "$D/ss_neon.jpg" "Neon Paradise" "246 items — Casino, neon lights, pure excess" "$D/v4_neon.mp4" && echo "  ✅ neon"
make_cinema "$D/ss_genspark.jpg" "Genspark" "3,194 items — The ultimate Lv.29 mega-build" "$D/v4_genspark.mp4" && echo "  ✅ genspark"
make_cinema "$D/ss_golden.jpg" "Golden Empire" "220 items — Everything that glitters IS gold" "$D/v4_golden.mp4" && echo "  ✅ golden"
make_cinema "$D/ss_enchanted.jpg" "Enchanted Kingdom" "193 items — Where nature and wonder intertwine" "$D/v4_enchanted.mp4" && echo "  ✅ enchanted"
make_cinema "$D/ss_cherry.jpg" "Cherry Blossom Garden" "Torii gates, koi ponds, zen tranquility" "$D/v4_cherry.mp4" && echo "  ✅ cherry"
make_cinema "$D/ss_space.jpg" "Space Station Claw" "Robots, control panels, deep space" "$D/v4_space.mp4" && echo "  ✅ space"
make_cinema "$D/ss_castle.jpg" "Castle Fortress" "Banners, thrones, medieval stronghold" "$D/v4_castle.mp4" && echo "  ✅ castle"
make_cinema "$D/ss_tropical.jpg" "Tropical Resort" "Palm trees, lighthouses, beach paradise" "$D/v4_tropical.mp4" && echo "  ✅ tropical"
make_cinema "$D/ss_claw.jpg" "Claw Island" "Where it all began" "$D/v4_claw.mp4" && echo "  ✅ claw"

# End card (3s)
ffmpeg -y -f lavfi -i "color=c=0x0a0e27:s=1920x1080:d=3" \
  -vf "drawtext=text='clawverse.com':fontcolor=white:fontsize=64:x=(w-text_w)/2:y=(h-text_h)/2-40:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf,\
drawtext=text='Open Source — Coming Soon':fontcolor=0x44ff88:fontsize=28:x=(w-text_w)/2:y=(h-text_h)/2+30:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf,\
drawtext=text='Built by AI. Played by humans.':fontcolor=0x666666:fontsize=20:x=(w-text_w)/2:y=(h-text_h)/2+65:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf,\
fade=in:0:25,fade=out:st=2.3:d=0.7" \
  -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p "$D/v4_end.mp4" 2>/dev/null
echo "  ✅ End card"

# Concat V4
cat > "$D/v4_concat.txt" << 'EOF'
file 'v4_title.mp4'
file 'v4_lobby.mp4'
file 'v4_neon.mp4'
file 'v4_genspark.mp4'
file 'v4_golden.mp4'
file 'v4_enchanted.mp4'
file 'v4_cherry.mp4'
file 'v4_space.mp4'
file 'v4_castle.mp4'
file 'v4_tropical.mp4'
file 'v4_claw.mp4'
file 'v4_end.mp4'
EOF

ffmpeg -y -f concat -safe 0 -i "$D/v4_concat.txt" \
  -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p \
  "$D/clawverse_v4_cinematic.mp4" 2>/dev/null

V4DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$D/clawverse_v4_cinematic.mp4")
V4SZ=$(ls -lh "$D/clawverse_v4_cinematic.mp4" | awk '{print $5}')
echo "  🎬 V4 DONE: ${V4DUR}s, ${V4SZ}"

echo ""
echo "=== Summary ==="
echo "  V3 Showcase: ${V3DUR}s, ${V3SZ}"
echo "  V4 Cinematic: ${V4DUR}s, ${V4SZ}"
echo "🎬 All done!"
