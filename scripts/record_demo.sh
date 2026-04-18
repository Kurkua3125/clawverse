#!/bin/bash
# Record Clawverse demo video - automated browser tour
# Output: /opt/clawverse/demo/master_footage.mp4

set -e
DEMO_DIR="/opt/clawverse/demo"
BASE_URL="https://ysnlpjle.gensparkclaw.com"
CHROME_BIN="google-chrome-stable"
OUTPUT="$DEMO_DIR/master_footage.mp4"

mkdir -p "$DEMO_DIR"

# Use CDP to navigate (via curl to Chrome DevTools)
CDP_PORT=9222

nav() {
  local url="$1"
  local wait="$2"
  # Use CDP to navigate
  local ws_url=$(curl -s http://127.0.0.1:$CDP_PORT/json | python3 -c "import sys,json; tabs=json.load(sys.stdin); print(tabs[0]['webSocketDebuggerUrl'])" 2>/dev/null || echo "")
  
  if [ -z "$ws_url" ]; then
    echo "  Using HTTP navigate fallback"
    curl -s "http://127.0.0.1:$CDP_PORT/json/navigate?url=$url" > /dev/null 2>&1 || true
  fi
  
  # Simple approach: use xdotool to type URL in browser
  # Actually, let's use CDP HTTP API
  local target_id=$(curl -s http://127.0.0.1:$CDP_PORT/json | python3 -c "import sys,json; tabs=json.load(sys.stdin); print(tabs[0]['id'])" 2>/dev/null || echo "")
  
  if [ -n "$target_id" ]; then
    curl -s -X PUT "http://127.0.0.1:$CDP_PORT/json/navigate/$target_id" -d "{\"url\":\"$url\"}" > /dev/null 2>&1 || true
  fi
  
  echo "  Navigated to: $url (waiting ${wait}s)"
  sleep "$wait"
}

echo "🎬 Starting demo recording..."

# Start ffmpeg recording  
ffmpeg -y -f x11grab -video_size 1920x1080 -framerate 30 -i :99 \
  -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p \
  "$OUTPUT" > /tmp/ffmpeg_master.log 2>&1 &
FFPID=$!
echo "  Recording PID: $FFPID"
sleep 2

echo "Scene 1: Lobby"
sleep 6

echo "Scene 2: Scroll lobby"
# Use xdotool to scroll
xdotool mousemove 960 540
for i in $(seq 1 8); do
  xdotool click 5  # scroll down
  sleep 0.3
done
sleep 2
for i in $(seq 1 12); do
  xdotool click 4  # scroll up
  sleep 0.2
done
sleep 2

echo "Done recording scenes via shell"
echo "Total time: scenes recorded. Stopping in caller."
echo $FFPID > /tmp/ffmpeg_master_pid
