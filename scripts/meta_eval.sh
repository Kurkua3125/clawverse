#!/bin/bash
# Meta-evaluation: GPT reviews the evolution PROCESS itself (not the product)
# Usage: bash scripts/meta_eval.sh <evolution_log_last_5_entries> <cron_message_file>
# Output: suggestions for improving the evolution system

set -e

LOG_FILE="/opt/clawverse/evolution_log.jsonl"
CRON_MSG="/opt/clawverse/scripts/cron_message.txt"
DI_FILE="/opt/clawverse/DESIGN_INTELLIGENCE.md"
STATE_FILE="/opt/clawverse/evolution_state.json"

# Collect last 5 sprint entries
LAST_5=$(tail -5 "$LOG_FILE" 2>/dev/null || echo "[]")

# Collect current cron message
CRON_CONTENT=$(cat "$CRON_MSG" 2>/dev/null || echo "N/A")

# Build the meta-eval prompt
PROMPT="You are a systems architect reviewing an AI self-evolution system. Your job is to make the SYSTEM ITSELF smarter, not the product.

Here are the last 5 evolution cycle logs (JSON, one per line):
---
$LAST_5
---

Here is the current evolution cycle instruction (the 'cron message' that drives each cycle):
---
$CRON_CONTENT
---

Analyze and answer:

1. PATTERN DETECTION: Look at the last 5 cycles. Are they doing diverse, impactful work? Or repeating similar small tweaks? Identify any anti-patterns (e.g., zoom adjusted 3 times, same CSS property tweaked repeatedly).

2. BLIND SPOTS: What types of issues is this system NOT finding? What user scenarios is it NOT testing? What parts of the product is it ignoring?

3. PROCESS IMPROVEMENTS: Suggest 1-3 specific changes to the cron message / evolution flow that would make the system smarter. Be concrete — write the exact text to add/change.

4. PRIORITY CALIBRATION: Is the system working on the right things? Or is it optimizing things that don't matter while ignoring things that do? What should the #1 priority be right now?

5. INTELLIGENCE CEILING: What is limiting this system's ability to improve? What structural change would raise the ceiling?

Be specific and actionable. Don't be polite — be useful."

# Create a temporary text file with the prompt (gsk analyze needs an image, so we use gsk search as workaround)
# Actually, let's use a different approach — write to a file and use gsk summarize
TEMP_FILE=$(mktemp /tmp/meta_eval_XXXXX.txt)
echo "$PROMPT" > "$TEMP_FILE"

# Convert text prompt to an image so gsk analyze can process it
echo "🧠 Running meta-evaluation of evolution system..."
PROMPT_IMG=$(mktemp /tmp/meta_eval_XXXXX.png)
python3 -c "
from PIL import Image, ImageDraw, ImageFont
import textwrap, sys

text = open('$TEMP_FILE').read()
# Wrap text
lines = []
for para in text.split('\n'):
    if para.strip():
        lines.extend(textwrap.wrap(para, width=100))
    else:
        lines.append('')

W, line_h = 1200, 16
H = max(800, len(lines) * line_h + 40)
img = Image.new('RGB', (W, H), 'white')
draw = ImageDraw.Draw(img)
try:
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf', 12)
except:
    font = ImageFont.load_default()

y = 20
for line in lines:
    draw.text((20, y), line, fill='black', font=font)
    y += line_h
    if y > H - 20:
        break

img.save('$PROMPT_IMG')
" 2>/dev/null

if [ -f "$PROMPT_IMG" ] && [ -s "$PROMPT_IMG" ]; then
    RESULT=$(gsk analyze -r "Read the text in this image carefully. It contains evolution system logs and a cron message. Follow ALL instructions in the text and provide your complete analysis for all 5 sections." -i "$PROMPT_IMG" 2>/dev/null || echo "META_EVAL_ERROR")
else
    # Fallback: use gsk web_search as a no-op and embed the question
    RESULT="META_EVAL_ERROR: Could not generate prompt image"
fi

rm -f "$TEMP_FILE" "$PROMPT_IMG"

# Extract and output
echo "$RESULT" | python3 -c "
import sys, json
raw = sys.stdin.read()
try:
    d = json.loads(raw)
    for r in d.get('data',{}).get('results',[]):
        text = r.get('result', '')
        print(text)
except:
    # If it's not JSON, print raw (might be error)
    print(raw[:3000])
" 2>/dev/null || echo "META_EVAL_PARSE_ERROR"
