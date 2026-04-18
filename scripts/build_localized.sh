#!/bin/bash
# Build Japanese and Korean versions of the demo video
set -e

S="/opt/clawverse/demo/pure"
V15="/opt/clawverse/demo/v15"
FONT_CJK="/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_EN="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

LANG_CODE="$1"  # ja or ko
OUT="/opt/clawverse/demo/v16_${LANG_CODE}"
mkdir -p "$OUT"

# Translations
if [ "$LANG_CODE" = "ja" ]; then
  TITLE_MAIN="CLAWVERSE"
  TITLE_SUB="ピクセルの島を作ろう"
  CTA_MAIN="島を作ろう"
  CTA_URL="genclawverse.ai"
  CTA_SUB="オープンソース — 今すぐプレイ"
  
  L_NEON="ネオンパラダイス"; S_NEON="246アイテム"
  L_GENSPARK="Genspark"; S_GENSPARK="3,194アイテム"
  L_GOLDEN="ゴールデンエンパイア"; S_GOLDEN="220アイテム"
  L_ENCHANTED="エンチャンテッドキングダム"; S_ENCHANTED="ファンタジーの森"
  L_CHERRY="桜庭園"; S_CHERRY="日本庭園"
  L_CASTLE="城砦"; S_CASTLE="中世の王国"
  L_SPACE="スペースステーション"; S_SPACE="SF基地"
  L_TROPICAL="トロピカルリゾート"; S_TROPICAL="ビーチパラダイス"
  L_LUCK="ラック"; S_LUCK="150アイテム"
  L_CLAW="クロー島"; S_CLAW="すべてはここから"
else
  TITLE_MAIN="CLAWVERSE"
  TITLE_SUB="픽셀 섬을 만들어보세요"
  CTA_MAIN="섬을 만들어보세요"
  CTA_URL="genclawverse.ai"
  CTA_SUB="오픈소스 — 지금 플레이"
  
  L_NEON="네온 파라다이스"; S_NEON="246 아이템"
  L_GENSPARK="Genspark"; S_GENSPARK="3,194 아이템"
  L_GOLDEN="골든 엠파이어"; S_GOLDEN="220 아이템"
  L_ENCHANTED="인챈티드 킹덤"; S_ENCHANTED="판타지 숲"
  L_CHERRY="벚꽃 정원"; S_CHERRY="일본식 정원"
  L_CASTLE="캐슬 포트리스"; S_CASTLE="중세 왕국"
  L_SPACE="스페이스 스테이션"; S_SPACE="SF 기지"
  L_TROPICAL="트로피컬 리조트"; S_TROPICAL="해변 파라다이스"
  L_LUCK="럭"; S_LUCK="150 아이템"
  L_CLAW="클로 아일랜드"; S_CLAW="모든 것이 시작된 곳"
fi

echo "=== Building $LANG_CODE version ==="

# We reuse the animated clips from v15 but add localized labels
# For animated clips, re-add labels in target language
add_label() {
  local inp="$1" label="$2" sub="$3" out="$4"
  ffmpeg -y -i "$inp" \
    -vf "drawbox=x=0:y=ih-65:w=iw:h=65:color=black@0.5:t=fill,drawtext=text='${label}':fontcolor=white:fontsize=26:x=30:y=h-48:fontfile=${FONT_CJK},drawtext=text='${sub}':fontcolor=0xbbbbbb:fontsize=15:x=30:y=h-20:fontfile=${FONT_CJK}" \
    -c:v libx264 -preset fast -crf 17 -pix_fmt yuv420p "$out" 2>/dev/null
}

# Use raw animated clips (without English labels) from v15
# They're anim_*.mp4 (no labels)
trim_anim() {
  local webm="$1" out="$2"
  local dur=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$webm" 2>/dev/null)
  local start=$(python3 -c "print(max(0, float('${dur}') - 5.5))")
  ffmpeg -y -ss "$start" -i "$webm" -t 4 -c:v libx264 -preset fast -crf 17 -pix_fmt yuv420p "$out" 2>/dev/null
}

make_static() {
  local img="$1" dur="$2" label="$3" sub="$4" dir="$5" out="$6"
  local ze frames=$((dur * 30))
  case "$dir" in
    in)  ze="z='min(zoom+0.0004,1.04)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'" ;;
    out) ze="z='if(eq(on,1),1.04,max(zoom-0.0004,1.0))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'" ;;
    left) ze="z=1.03:x='iw*0.015+iw*0.015*on/${frames}':y='ih/2-(ih/zoom/2)'" ;;
    right) ze="z=1.03:x='iw*0.03-iw*0.015*on/${frames}':y='ih/2-(ih/zoom/2)'" ;;
  esac
  local vf="scale=2160:1215,crop=1920:1080,zoompan=${ze}:d=${frames}:s=1920x1080:fps=30"
  vf="${vf},drawbox=x=0:y=ih-65:w=iw:h=65:color=black@0.5:t=fill,drawtext=text='${label}':fontcolor=white:fontsize=26:x=30:y=h-48:fontfile=${FONT_CJK},drawtext=text='${sub}':fontcolor=0xbbbbbb:fontsize=15:x=30:y=h-20:fontfile=${FONT_CJK}"
  ffmpeg -y -loop 1 -i "$img" -vf "$vf" -t "$dur" -c:v libx264 -preset fast -crf 17 -pix_fmt yuv420p "$out" 2>/dev/null
}

A="/opt/clawverse/demo/animated"

# Title
ffmpeg -y -loop 1 -i "$S/neon.png" \
  -vf "scale=2160:1215,crop=1920:1080,zoompan=z='min(zoom+0.0003,1.03)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=60:s=1920x1080:fps=30,eq=brightness=-0.3,drawtext=text='${TITLE_MAIN}':fontcolor=white:fontsize=88:x=(w-text_w)/2:y=(h-text_h)/2-40:fontfile=${FONT_EN},drawtext=text='${TITLE_SUB}':fontcolor=0x66ccff:fontsize=28:x=(w-text_w)/2:y=(h-text_h)/2+35:fontfile=${FONT_CJK}" \
  -t 2 -c:v libx264 -preset fast -crf 17 -pix_fmt yuv420p "$OUT/title.mp4" 2>/dev/null
echo "  ✅ title"

# Animated clips with localized labels
trim_anim "$A/neon.webm" "$OUT/raw_neon.mp4"
add_label "$OUT/raw_neon.mp4" "$L_NEON" "$S_NEON" "$OUT/a_neon.mp4"
echo "  ✅ neon"

trim_anim "$A/genspark.webm" "$OUT/raw_genspark.mp4"
add_label "$OUT/raw_genspark.mp4" "$L_GENSPARK" "$S_GENSPARK" "$OUT/a_genspark.mp4"
echo "  ✅ genspark"

trim_anim "$A/enchanted.webm" "$OUT/raw_enchanted.mp4"
add_label "$OUT/raw_enchanted.mp4" "$L_ENCHANTED" "$S_ENCHANTED" "$OUT/a_enchanted.mp4"
echo "  ✅ enchanted"

trim_anim "$A/tropical.webm" "$OUT/raw_tropical.mp4"
add_label "$OUT/raw_tropical.mp4" "$L_TROPICAL" "$S_TROPICAL" "$OUT/a_tropical.mp4"
echo "  ✅ tropical"

trim_anim "$A/claw.webm" "$OUT/raw_claw.mp4"
add_label "$OUT/raw_claw.mp4" "$L_CLAW" "$S_CLAW" "$OUT/a_claw.mp4"
echo "  ✅ claw"

trim_anim "$A/space.webm" "$OUT/raw_space.mp4"
add_label "$OUT/raw_space.mp4" "$L_SPACE" "$S_SPACE" "$OUT/a_space.mp4"
echo "  ✅ space"

trim_anim "$A/luck.webm" "$OUT/raw_luck.mp4"
add_label "$OUT/raw_luck.mp4" "$L_LUCK" "$S_LUCK" "$OUT/a_luck.mp4"
echo "  ✅ luck"

# Static clips
make_static "$S/golden.png"  2 "$L_GOLDEN"  "$S_GOLDEN"  "left"  "$OUT/s_golden.mp4"
make_static "$S/cherry.png"  2 "$L_CHERRY"  "$S_CHERRY"  "right" "$OUT/s_cherry.mp4"
make_static "$S/castle.png"  2 "$L_CASTLE"  "$S_CASTLE"  "out"   "$OUT/s_castle.mp4"
echo "  ✅ static clips"

# CTA
ffmpeg -y -f lavfi -i "color=c=0x0a0e27:s=1920x1080:d=3" \
  -vf "drawtext=text='${CTA_MAIN}':fontcolor=white:fontsize=72:x=(w-text_w)/2:y=(h-text_h)/2-50:fontfile=${FONT_CJK},drawtext=text='${CTA_URL}':fontcolor=0x44ff88:fontsize=36:x=(w-text_w)/2:y=(h-text_h)/2+30:fontfile=${FONT_EN},drawtext=text='${CTA_SUB}':fontcolor=0x888888:fontsize=22:x=(w-text_w)/2:y=(h-text_h)/2+75:fontfile=${FONT_CJK}" \
  -c:v libx264 -preset fast -crf 17 -pix_fmt yuv420p "$OUT/cta.mp4" 2>/dev/null
echo "  ✅ cta"

# Assemble
cat > "$OUT/concat.txt" << CEOF
file 'title.mp4'
file 'a_neon.mp4'
file 's_golden.mp4'
file 'a_genspark.mp4'
file 's_cherry.mp4'
file 'a_enchanted.mp4'
file 's_castle.mp4'
file 'a_space.mp4'
file 'a_tropical.mp4'
file 'a_luck.mp4'
file 'a_claw.mp4'
file 'cta.mp4'
CEOF

ffmpeg -y -f concat -safe 0 -i "$OUT/concat.txt" -c:v libx264 -preset medium -crf 17 -pix_fmt yuv420p "$OUT/silent.mp4" 2>/dev/null

dur=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$OUT/silent.mp4" 2>/dev/null)
echo "  🎬 Silent ${LANG_CODE}: ${dur}s"
