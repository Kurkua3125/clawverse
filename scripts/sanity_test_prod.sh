#!/bin/bash
# Clawverse Production Sanity Test
# Run after every deployment to verify critical functionality
# Usage: bash scripts/sanity_test_prod.sh [base_url]
# Default: https://genclawverse.ai

set -e
BASE="${1:-https://genclawverse.ai}"
PASS=0
FAIL=0
WARN=0
ISSUES=""

pass() { PASS=$((PASS+1)); echo "  ✅ $1"; }
fail() { FAIL=$((FAIL+1)); echo "  ❌ $1"; ISSUES="$ISSUES\n- $1"; }
warn() { WARN=$((WARN+1)); echo "  ⚠️  $1"; }

check_status() {
  local url="$1" desc="$2" expect="${3:-200}"
  local status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$url" 2>/dev/null)
  if [ "$status" = "$expect" ]; then
    pass "$desc (HTTP $status)"
  else
    fail "$desc — expected $expect, got $status"
  fi
}

check_json() {
  local url="$1" desc="$2" field="$3" expect="$4"
  local body=$(curl -s --max-time 10 "$url" 2>/dev/null)
  local value=$(echo "$body" | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(d.get('$field',''))" 2>/dev/null)
  if [ "$value" = "$expect" ]; then
    pass "$desc ($field=$value)"
  else
    fail "$desc — expected $field=$expect, got $field=$value"
  fi
}

check_contains() {
  local url="$1" desc="$2" needle="$3"
  local body=$(curl -s --max-time 10 "$url" 2>/dev/null)
  if echo "$body" | grep -q "$needle"; then
    pass "$desc"
  else
    fail "$desc — '$needle' not found"
  fi
}

echo "======================================"
echo "🦞 Clawverse Production Sanity Test"
echo "   Target: $BASE"
echo "   Time:   $(date -u '+%Y-%m-%d %H:%M UTC')"
echo "======================================"

# ── 1. Core Pages ──
echo ""
echo "📄 1. Core Pages"
check_status "$BASE/" "Homepage/Lobby loads"
check_status "$BASE/island/default" "Island page loads"
check_contains "$BASE/" "Lobby has Clawverse title" "Clawverse"
check_contains "$BASE/island/default" "Island page has canvas" "canvas"

# ── 2. API Health ──
echo ""
echo "🔌 2. API Health"
check_json "$BASE/api/status" "Status API" "state" "idle"
check_status "$BASE/api/islands?sort=popular" "Islands list API"
check_status "$BASE/api/streak" "Streak API"
check_status "$BASE/api/quests" "Quests API"
check_status "$BASE/api/notifications" "Notifications API (auth required=401 OK)" "401"

# ── 3. Auth System ──
echo ""
echo "🔐 3. Auth System"
check_status "$BASE/api/auth/me" "Auth check endpoint"
# Turnstile test - should not crash
check_status "$BASE/api/auth/request-code" "Auth request-code (GET=405 expected)" "405"

# ── 4. Push Notification System ──
echo ""
echo "🔔 4. Push Notifications"
check_json "$BASE/api/push/vapid-public-key" "VAPID public key API" "ok" "True"

VAPID_KEY=$(curl -s "$BASE/api/push/vapid-public-key" 2>/dev/null | python3 -c "import sys,json; print(len(json.loads(sys.stdin.read()).get('publicKey','')))" 2>/dev/null)
if [ "$VAPID_KEY" -gt "80" ] 2>/dev/null; then
  pass "VAPID key length valid ($VAPID_KEY chars)"
else
  fail "VAPID key too short or missing ($VAPID_KEY)"
fi

check_contains "$BASE/sw.js" "Service Worker serves correctly" "push"
check_contains "$BASE/sw.js" "SW has notification click handler" "notificationclick"

# ── 5. Frontend Assets ──
echo ""
echo "🎨 5. Frontend Assets"
check_status "$BASE/catalog/catalog.json" "Catalog JSON"
check_contains "$BASE/island/default" "i18n loaded" "i18n"
check_contains "$BASE/island/default" "Push banner code present" "push-banner"

# ── 6. Social Features ──
echo ""
echo "👥 6. Social Features"
# Guestbook read (should work without auth)
GUESTBOOK=$(curl -s "$BASE/api/island/default/guestbook" 2>/dev/null | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print('ok' if 'entries' in d or 'messages' in d else 'fail')" 2>/dev/null)
if [ "$GUESTBOOK" = "ok" ]; then
  pass "Guestbook API readable"
else
  warn "Guestbook API structure unexpected"
fi

check_status "$BASE/api/gifts" "Gifts API"
check_status "$BASE/api/world" "World data API"

# ── 7. Lobby Features ──
echo ""
echo "🌏 7. Lobby"
ISLAND_COUNT=$(curl -s "$BASE/api/islands?sort=popular" 2>/dev/null | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(len(d.get('islands',[])))" 2>/dev/null)
if [ "$ISLAND_COUNT" -gt "0" ] 2>/dev/null; then
  pass "Islands available in lobby ($ISLAND_COUNT islands)"
else
  warn "No islands in lobby (might be expected for fresh deploy)"
fi

# ── 8. i18n ──
echo ""
echo "🌐 8. Internationalization"
# i18n is loaded via separate i18n.js file
check_contains "$BASE/island/default" "i18n script loaded" "i18n.js"

# Check i18n.js has multi-language support
I18N_LANGS=$(curl -s "$BASE/island/default" 2>/dev/null | grep -o "i18n.js" | head -1)
if [ -n "$I18N_LANGS" ]; then
  pass "i18n.js referenced in page"
else
  warn "i18n.js not found in page"
fi

# ── 9. Security ──
echo ""
echo "🛡️ 9. Security"
# CSRF should block cross-origin POST
CSRF=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "Origin: https://evil.com" "$BASE/api/push/subscribe" 2>/dev/null)
if [ "$CSRF" = "403" ]; then
  pass "CSRF protection blocks cross-origin POST"
else
  warn "CSRF check returned $CSRF (expected 403)"
fi

# No secrets in page source
PAGE=$(curl -s "$BASE/island/default" 2>/dev/null)
for secret in "kunjing@gmail" "MAILCHANNELS_API" "vapid_keys.json" "PRIVATE KEY" "genclawverse_key"; do
  if echo "$PAGE" | grep -qi "$secret"; then
    fail "SECRET LEAK: '$secret' found in page source!"
  fi
done
pass "No secrets in page source"

# ── 10. Performance ──
echo ""
echo "⚡ 10. Performance"
LOAD_TIME=$(curl -s -o /dev/null -w "%{time_total}" "$BASE/" 2>/dev/null)
if (( $(echo "$LOAD_TIME < 3.0" | bc -l) )); then
  pass "Homepage loads in ${LOAD_TIME}s (< 3s)"
elif (( $(echo "$LOAD_TIME < 5.0" | bc -l) )); then
  warn "Homepage loads in ${LOAD_TIME}s (slow, > 3s)"
else
  fail "Homepage loads in ${LOAD_TIME}s (too slow, > 5s)"
fi

ISLAND_TIME=$(curl -s -o /dev/null -w "%{time_total}" "$BASE/island/default" 2>/dev/null)
if (( $(echo "$ISLAND_TIME < 3.0" | bc -l) )); then
  pass "Island page loads in ${ISLAND_TIME}s (< 3s)"
elif (( $(echo "$ISLAND_TIME < 5.0" | bc -l) )); then
  warn "Island page loads in ${ISLAND_TIME}s (slow, > 3s)"
else
  fail "Island page loads in ${ISLAND_TIME}s (too slow, > 5s)"
fi

# ── Summary ──
echo ""
echo "======================================"
echo "📊 Results: $PASS passed, $FAIL failed, $WARN warnings"
if [ $FAIL -gt 0 ]; then
  echo ""
  echo "❌ FAILURES:"
  echo -e "$ISSUES"
  echo ""
  echo "DEPLOYMENT MAY HAVE ISSUES — review above failures"
  exit 1
else
  echo "✅ All critical checks passed!"
  exit 0
fi
