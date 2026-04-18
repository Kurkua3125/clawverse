#!/bin/bash
# Clawverse External Evaluation Script
# Captures screenshots and runs blind eval via gsk analyze (external model)
# Usage: bash scripts/run_eval.sh [--compare prev_dir]

set -e

SITE="https://ysnlpjle.gensparkclaw.com"
TIMESTAMP=$(date -u +"%Y-%m-%d-%H%M")
EVAL_DIR="/opt/clawverse/eval-results/eval-${TIMESTAMP}"
SCREENSHOT_DIR="${EVAL_DIR}/screenshots"
export SCREENSHOT_DIR
mkdir -p "$SCREENSHOT_DIR"

echo "=== Clawverse External Eval — $TIMESTAMP ==="
echo "Output: $EVAL_DIR"

# ── Step 1: Capture screenshots via Playwright ──
echo ""
echo "📸 Capturing screenshots..."

python3 - <<'PYEOF'
import subprocess, sys, os, time

SITE = "https://ysnlpjle.gensparkclaw.com"
SDIR = os.environ.get("SCREENSHOT_DIR", "/tmp/eval-screenshots")

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Installing playwright...")
    subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], check=True, capture_output=True)
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True, capture_output=True)
    from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    
    screenshots = [
        ("lobby_desktop", "/", 1280, 800, False),
        ("lobby_mobile", "/", 390, 844, False),
        ("island_desktop_visitor", "/island/test", 1280, 800, False),
        ("island_mobile_visitor", "/island/test", 390, 844, False),
    ]
    
    for name, path, w, h, full_page in screenshots:
        ctx = browser.new_context(viewport={"width": w, "height": h})
        ctx.clear_cookies()
        page = ctx.new_page()
        page.evaluate("() => { try { localStorage.clear(); } catch(e) {} }")
        page.goto(f"{SITE}{path}", wait_until="load", timeout=20000)
        time.sleep(3)  # Wait for animations
        page.screenshot(path=f"{SDIR}/{name}.png", full_page=full_page)
        print(f"  ✅ {name} ({w}x{h})")
        ctx.close()
    
    # Mobile interaction screenshots
    ctx = browser.new_context(viewport={"width": 390, "height": 844})
    ctx.clear_cookies()
    page = ctx.new_page()
    page.goto(f"{SITE}/island/test", wait_until="load", timeout=20000)
    time.sleep(3)
    
    # Shop panel
    try:
        page.evaluate("() => { if(typeof toggleShopBar==='function') toggleShopBar(); }")
        time.sleep(1)
        page.screenshot(path=f"{SDIR}/island_mobile_shop.png")
        print("  ✅ island_mobile_shop")
        page.evaluate("() => { if(typeof closeShopBar==='function') closeShopBar(); }")
    except: print("  ⚠️ shop screenshot failed")
    
    # More menu
    try:
        page.evaluate("() => { if(typeof toggleMoreMenu==='function') toggleMoreMenu(); }")
        time.sleep(1)
        page.screenshot(path=f"{SDIR}/island_mobile_more.png")
        print("  ✅ island_mobile_more")
        page.evaluate("() => { if(typeof toggleMoreMenu==='function') toggleMoreMenu(); }")
    except: print("  ⚠️ more menu screenshot failed")
    
    # Guestbook
    try:
        page.evaluate("() => { if(typeof toggleGuestbook==='function') toggleGuestbook(); }")
        time.sleep(1)
        page.screenshot(path=f"{SDIR}/island_mobile_guestbook.png")
        print("  ✅ island_mobile_guestbook")
    except: print("  ⚠️ guestbook screenshot failed")
    
    ctx.close()
    browser.close()

print("📸 All screenshots captured!")
PYEOF

# ── Step 2: Run external eval via gsk analyze ──
echo ""
echo "🧠 Running external model evaluation..."

EVAL_RESULTS="${EVAL_DIR}/eval_results.json"
echo "[]" > "$EVAL_RESULTS"

run_eval_prompt() {
    local img="$1"
    local prompt_name="$2"
    local prompt_text="$3"
    local img_name=$(basename "$img" .png)
    
    echo "  Evaluating: ${img_name} — ${prompt_name}..."
    
    local result
    result=$(gsk analyze -r "$prompt_text" -i "$img" 2>/dev/null || echo "EVAL_ERROR")
    
    # Save individual result
    local outfile="${EVAL_DIR}/${img_name}_${prompt_name}.txt"
    echo "$result" > "$outfile"
    echo "    → saved to $(basename $outfile)"
}

# Eval Prompt 1: First Impression
PROMPT_1="You are seeing this website/app screen for the very first time. You have 3 seconds. Answer:
1. What do you think this site IS? (one sentence)
2. What would you click/tap first? Why?
3. Score CLARITY from 1-10 (10=instantly obvious what to do, 1=completely confused)
4. Score VISUAL APPEAL from 1-10
5. What is the single most confusing element on screen?
Be brutally honest. This is a blind review."

# Eval Prompt 2: Usability Audit
PROMPT_2="You are a senior UX auditor. Examine this screen and find ALL usability problems.
For each issue:
- WHAT is wrong (be specific — element name, location)
- WHY it matters to the user (what goes wrong in their experience)
- SEVERITY: critical / major / minor / cosmetic
Find at least 5 issues. Be harsh — pretend you're being paid to find problems, not praise.
Also note: anything that looks broken, clipped, overlapping, or illegible."

# Eval Prompt 3: User Journey
PROMPT_3="A 14-year-old just received a link to this page from a friend on Discord. The friend said 'check out my island!'
Walk through step by step what this teen would do:
1. What's their first reaction seeing this screen?
2. What would they tap/click? 
3. Where would they get CONFUSED?
4. Where would they get BORED and leave?
5. Where would they be DELIGHTED?
6. Would they create their own island? Why/why not?
7. Would they share this with another friend? Why/why not?
Score RETENTION LIKELIHOOD 1-10 (would they come back tomorrow?)"

# Run evals on key screenshots
for img in "$SCREENSHOT_DIR"/lobby_mobile.png "$SCREENSHOT_DIR"/island_mobile_visitor.png "$SCREENSHOT_DIR"/island_mobile_shop.png "$SCREENSHOT_DIR"/island_mobile_guestbook.png "$SCREENSHOT_DIR"/island_mobile_more.png; do
    [ -f "$img" ] || continue
    run_eval_prompt "$img" "first_impression" "$PROMPT_1"
    run_eval_prompt "$img" "usability_audit" "$PROMPT_2"
done

# User journey eval on the full mobile flow
if [ -f "$SCREENSHOT_DIR/island_mobile_visitor.png" ]; then
    run_eval_prompt "$SCREENSHOT_DIR/island_mobile_visitor.png" "user_journey" "$PROMPT_3"
fi

# Also eval desktop
for img in "$SCREENSHOT_DIR"/lobby_desktop.png "$SCREENSHOT_DIR"/island_desktop_visitor.png; do
    [ -f "$img" ] || continue
    run_eval_prompt "$img" "first_impression" "$PROMPT_1"
    run_eval_prompt "$img" "usability_audit" "$PROMPT_2"
done

# ── Step 3: Naive Agent Test ──
echo ""
echo "🦞 Running naive agent (小白) comparison..."

NAIVE_PROMPT="Look at this screenshot of a website. You know nothing about it — you've never seen it before.
List every single problem, confusing element, ugly thing, broken thing, or missed opportunity you can find.
Don't hold back. Find at least 10 things wrong. Include:
- Visual problems (alignment, spacing, contrast, clutter)
- Text problems (too small, too much, unclear labels)
- Interaction problems (what would a user expect to happen?)
- Missing features (what should be here but isn't?)
- Mobile-specific issues (touch targets, thumb zones, screen real estate)
Number each issue. Be specific about location on screen."

for img in "$SCREENSHOT_DIR"/island_mobile_visitor.png "$SCREENSHOT_DIR"/lobby_mobile.png; do
    [ -f "$img" ] || continue
    run_eval_prompt "$img" "naive_agent" "$NAIVE_PROMPT"
done

# ── Step 4: Summary ──
echo ""
echo "=== Eval Complete ==="
echo "Results: $EVAL_DIR"
echo "Screenshots: $(ls $SCREENSHOT_DIR/*.png 2>/dev/null | wc -l)"
echo "Eval files: $(ls $EVAL_DIR/*.txt 2>/dev/null | wc -l)"
echo ""
echo "To review: ls $EVAL_DIR/"
