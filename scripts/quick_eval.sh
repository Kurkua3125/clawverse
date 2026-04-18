#!/bin/bash
# Quick single-screenshot eval via GPT (gsk analyze)
# Usage: bash scripts/quick_eval.sh <screenshot_path> [prompt_type]
# prompt_type: "audit" (default), "first_impression", "journey"
# Returns the eval text to stdout

set -e

IMG="$1"
TYPE="${2:-audit}"

if [ ! -f "$IMG" ]; then
    echo "ERROR: File not found: $IMG" >&2
    exit 1
fi

case "$TYPE" in
    audit)
        PROMPT="You are a harsh UX auditor reviewing a mobile game website screenshot. Find ALL problems:
1. List every usability issue (WHAT is wrong, WHERE on screen, WHY it hurts users, SEVERITY: critical/major/minor)
2. Score overall UX quality 1-10
3. What is the SINGLE most important thing to fix?
4. What would make a first-time visitor leave immediately?
5. What would delight them?
Find at least 5 real issues. No praise — only problems and solutions."
        ;;
    first_impression)
        PROMPT="3-second test: You see this screen for the first time.
1. What IS this? (one sentence)
2. What would you do first?
3. Clarity score 1-10
4. Visual appeal score 1-10  
5. Most confusing element?
6. Would you stay or leave? Why?"
        ;;
    journey)
        PROMPT="A 14-year-old got this link from a friend on Discord ('check out my island!').
1. First reaction?
2. What would they tap?
3. Where would they get confused?
4. Where would they get bored and leave?
5. Would they create their own island?
6. Would they share with friends?
7. Retention score 1-10 (come back tomorrow?)"
        ;;
    compare)
        PROMPT="Compare these two versions of the same website. For each difference:
1. Which version is better and why?
2. Any regressions (things that got worse)?
3. Overall: did the changes improve the user experience?
4. Score improvement: -5 to +5 (0=no change, negative=got worse)"
        ;;
esac

# Run gsk analyze and extract result text
RESULT=$(gsk analyze -r "$PROMPT" -i "$IMG" 2>/dev/null)

# Extract just the result text
echo "$RESULT" | python3 -c "
import sys, json
try:
    d = json.loads(sys.stdin.read())
    for r in d.get('data',{}).get('results',[]):
        text = r.get('result','')
        # Remove the detailed image description if present
        if 'Detailed scene' in text:
            text = text[:text.index('Detailed scene')].strip()
        elif 'Comprehensive description' in text:
            text = text[:text.index('Comprehensive description')].strip()
        print(text)
except:
    print('EVAL_PARSE_ERROR')
" 2>/dev/null || echo "EVAL_ERROR"
