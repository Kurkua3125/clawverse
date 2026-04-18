# Clawverse Issues Backlog

## 🎯 Core Design Principles (PERMANENT — Never Violate)

### P1: Mobile-First, Clutter-Free
**Source:** Eric's direct feedback (2026-03-22) — mobile UI is too crowded, too much information on screen at once.
**Rule:** Every UI element must justify its presence on a 390px screen. When in doubt, hide it behind a tap.
- New users should see the **island map** as the primary focus, not toolbars/panels/popups competing for attention
- Minimize simultaneous floating elements (popups, suggestion panels, chat bubbles, info bars)
- Topbar: absolute minimum items. Collapse aggressively on mobile.
- Bottom nav: clean, simple, no overlap with content
- Modals/panels: one at a time, never stacked
- "Explore more islands" and other secondary panels: hidden by default on mobile, accessible via tap

### P2: Onboarding Simplicity
**Source:** Eric's direct feedback (2026-03-22) — think from a first-time user's perspective.
**Rule:** A brand new user who has never seen Clawverse should understand what to do within 5 seconds of landing.
- First screen = the map. Not stats, not leaderboards, not activity feeds.
- Progressive disclosure: show basics first, reveal depth as the user explores
- No jargon without context (what's a "fort"? what does "Lv.2" mean?)
- Touch targets ≥ 44px on mobile
- Reduce cognitive load: fewer choices upfront, guide the user step by step

---

## 🔴 Critical (Fix Now)

### ISSUE-013: Mobile UI Decluttering (HIGH PRIORITY) — ✅ COMPLETE (multiple sprints)
**Problem:** On mobile island view, too many elements compete for screen space simultaneously:
- Top toolbar with Bag/Shop/Land/icons
- Island info bar (name, owner, level, type, visits)
- "Explore more islands" suggestion panel floating over map
- Lobster chat bubble overlapping content
- Island description text at bottom
- Bottom nav bar (View/Build/Chat/More)
**Result:** The actual island map — the core experience — gets squeezed. New users are overwhelmed.
**Fix plan:**
- [x] Collapse top toolbar on mobile: hide Bag/Shop/Land/Guestbook/Share/Lobby buttons (evo-030)
- [x] Reduce topbar height 48px→42px on mobile (evo-030)
- [x] Hide visitor-info-bar entirely on mobile — info shown in welcome modal instead (evo-030)
- [x] "Explore more islands" panel: hidden on mobile via CSS (evo-030)
- [x] Island bio panel: hidden on mobile (evo-030)
- [x] Bottom nav updated: View/Bag/Shop/Book/More — replaces hidden topbar buttons (evo-030)
- [x] Lobster chat: smaller on mobile (200px/11px), dismissible (✕ button), first-visit-only per island via localStorage (evo-031)
- [x] Map occupies ~90% of viewport on mobile — verified via console log diagnostic (evo-031)
- [x] Daily bulletin bar: mobile-friendly (smaller text, shorter duration 4s, tap-to-dismiss, correct top offset) (evo-031)
- [x] Claw auto-poll reduced: visitors get one-time check only, no 60s interval (evo-031)
- [x] Welcome modal → compact bottom sheet on mobile: map visible above, guestbook collapsed behind toggle, slide-up animation (evo-032)

### ISSUE-014: Mobile Island — No Island Name/Context Visible — ✅ FIXED (evo-050)
**Found:** UX Audit 2026-03-22
**Problem:** On mobile (390px), visiting an island shows NO island name, NO owner name, NO level — just "← Bac..." (truncated), "⋯", "Visiting · Log in".
**Fix:**
- [x] `#hud-name` max-width increased 140→200px (≤600px) and 120→170px (≤400px) — island name no longer truncated
- [x] Mobile visitor view shows just "🏝️ Test" (island name only), desktop shows "🏝️ Test by 🦞 Eric J"
- [x] "← Lobby" replaced with just "←" on mobile (font-size:0 + ::before pseudo-element)
- [x] Fixed ≤400px media query that was overriding the ← arrow-only display

### ISSUE-015: "More" Menu Overwhelms New Users — ✅ FIXED (evo-050)
**Found:** UX Audit 2026-03-22
**Problem:** The "More" menu showed 17 items in a flat list to everyone including visitors.
**Fix:**
- [x] Menu items tagged with `data-role="all"` (visitor-visible) or `data-role="owner"` (owner-only)
- [x] Visitors see 5 items: All Islands, Guestbook, Share, Leaderboard, Help, World Map, Events
- [x] Owner-only items (Achievements, Farm Panel, Snapshot, Statistics, Customize, AI Layout, Story, Messages, Defense, Export PNG, Analytics, API Settings) hidden for visitors via JS toggle
- [x] Dividers separate visitor and owner sections

### ISSUE-016: Lobster Chat Shows Owner-Only Info to Visitors — ✅ FIXED (evo-051)
**Found:** UX Audit 2026-03-22
**Problem:** Lobster shows "6 crop(s) are ready to harvest!" to visitors who can't actually harvest anything.
**Fix:**
- [x] Backend: `/api/claw/action?visitor=1` returns visitor-appropriate messages based on island object count
- [x] Frontend: `checkClawAction()` passes `visitor=1` when `!isOwner`
- [x] Visitors see welcome/explore messages; owners still see harvest/plant/guard messages

### ISSUE-017: Mobile Lobby — Too Much Above the Fold Before Islands — ✅ FIXED (evo-051)
**Found:** UX Audit 2026-03-22
**Problem:** On mobile, user has to scroll past: title, subtitle, stats, "Recent Activity" (collapsed), "Leaderboard" (collapsed), "Islands (31)", filter bar (Popular/Recent/Random/All/Farm/Fish/Mine/Forest), "Create Your Island" CTA — all before seeing a single island card.
**Fix:**
- [x] Hero stats and online count hidden on mobile (display:none)
- [x] Activity Feed and Leaderboard sections hidden entirely on mobile
- [x] Hero section compacted: smaller title (14px), tighter padding
- [x] "Filter" label hidden on mobile
- [x] CTA banner compacted: hidden emoji/subtitle, smaller button
- [x] Section titles compacted (12px)
- AI rates mobile lobby 7/10 (up from ~6/10) — island cards now visible much sooner

### ISSUE-018: Guestbook Panel Covers Entire Screen on Mobile — ✅ FIXED (evo-052)
**Found:** UX Audit 2026-03-22
**Problem:** Guestbook slides in from the right and covers ~95% of the screen. Bottom nav is almost entirely hidden. The form input is at the very bottom edge.
**Fix:**
- [x] Guestbook converted to bottom sheet on mobile (≤600px): slides up from bottom, max 60vh, rounded top corners
- [x] Drag handle pill indicator at top for visual affordance
- [x] Bottom nav remains visible (panel sits above 52px nav bar)
- [x] Entries area capped at 30vh, input area compact (8px padding)
- [x] Desktop behavior unchanged (still slides from right)

### ISSUE-022: Island Visitor Information Hierarchy — ✅ FIXED (evo-052, refined evo-053)
**Found:** AI Visual Analysis (gsk analyze) rated island info hierarchy 4/10 → 5/10
**Problem:** Visitors see "Visiting · Log in" but no context about the island (type, level, objects, visits). No clear sense of what they're looking at.
**Fix:**
- [x] Added floating visitor context chip below topbar: "🏝️ Island · Lv.7 · 166 objects · 43 visits" (evo-052)
- [x] Subtle translucent pill design, non-intrusive (evo-052)
- [x] 1.5s fade-in delay to avoid competing with welcome modal (evo-052)
- [x] Mobile responsive (10px font, tighter padding on ≤600px) (evo-052)
- [x] Only shown to visitors (hidden for island owners) (evo-052)
- [x] **Merged context chip INTO topbar** — eliminated standalone floating pill, stats now inline next to island name (evo-053)
- [x] Desktop: "Lv.X · N objects · N visits" in subtle #a0b8cc text next to island name
- [x] Mobile: condensed "Lv.X · Nv" to save space (evo-053)

---

### ~~ISSUE-001: Lobby visit counts all show 0~~ ✅ FIXED (evo-001)
- Added `page_views` table with IP dedup (1/hr). Combined page_views + visits in lobby query.
- Added `POST /api/pageview` endpoint + auto-tracking on island page load.

### ~~ISSUE-002: Token/API key architecture for public deployment~~ ✅ FIXED (evo-003b sub-agent)
- Added `user_settings` table, GET/POST/DELETE `/api/settings/apikey`, POST `/api/ai/check`
- Frontend settings modal (⚙️ in ⋯ menu) with provider selector, usage bar, key management
- Rate limiting: 50 AI calls/day per user, auto-reset at midnight UTC

## 🟡 Medium Priority

### ~~ISSUE-003: Lobby UX improvements~~ ✅ COMPLETE
- ✅ Sorting: Popular/Recent buttons (evo-002)
- ✅ Island type badges: farm/fish/mine/forest (evo-002)
- ✅ "Anonymous" → "demo island" label (evo-002)
- ✅ Grammar: "1 visit" not "1 visits" (evo-002)
- ✅ Favicon added (evo-003)
- ✅ Empty thumbnail placeholder 🏝️ (evo-003)
- ✅ Stats/owner text readability improved (evo-003)
- ✅ Island name ellipsis — already in lobby CSS (evo-004 audit)
- ✅ Search/filter by island name or owner (evo-004)
- ✅ Island count in section title, e.g. "Islands (31)" (evo-004)
- ✅ Collapsible login form — compact Join/Login button (evo-008)
- ✅ Island type filter buttons: All/🌾/🐟/⛏️/🌲 (evo-008)
- ✅ Live player count in hero section (evo-008)

### ISSUE-004: Mobile experience — PARTIALLY DONE
- ✅ Topbar overflow fix: hide island-type badge, compact buttons on <600px (evo-006)
- ✅ API settings modal responsive (evo-006)
- ✅ Island name truncation on <400px (evo-006)
- ✅ Mobile card text bump: island-name 14px, owner 11px, stats 11px with brighter color (evo-014)
- ✅ Mobile card thumbnails taller (160px), extra-small screen fallback at 380px (evo-014)
- ✅ Stats row touch targets: min-height 32px inline-flex (evo-014)
- ✅ Keyboard navigation: WASD/arrow keys pan, +/- zoom on island view (evo-023)
- ✅ Mobile card simplification: hide bio, reduce stats to essentials, name→16px, stats→14px, better line-height/padding (evo-028)
- Touch interactions on the isometric canvas — needs testing
- ✅ Bottom nav integration: updated with Bag/Shop/Book/More (evo-030)
- ✅ Minimap hidden for visitors on mobile — was showing as dark square artifact (evo-033)
- ✅ Minimap hidden for visitors on desktop too — display:none by default, body.owner-view overrides (evo-036)
- ✅ Camera auto-centers on actual island content instead of grid center — visitors now see the island properly (evo-033)
- ✅ Camera zoom improved: island fills ~90% of viewport instead of ~55%, buildings/objects much larger and more visible (evo-034)
- ✅ "Explore more islands" panel: fixed-position at bottom of viewport on desktop, better contrast/opacity, close button, larger text (evo-034)
- ✅ Bottom bar polished: clock shows "Mar 22" instead of debug-like UTC timestamp, presence badge shows "🟢 N online" with pulse animation, weather badge capitalized (evo-038)
- ✅ Bottom bar shimmer: animated gradient top border for game-like polish (evo-038)
- ✅ Mobile welcome bottom sheet compacted: 45vh→30vh, hidden emoji/stats, smaller padding/buttons — sheet takes ~25% of viewport instead of ~45% (evo-035)
- ✅ Desktop welcome modal: blur reduced 3px→1px, overlay 0.42→0.25 so island visible behind; "Log in" demoted to text link for clear CTA hierarchy (evo-035)
- ✅ Daily bulletin bar suppressed when welcome modal is visible on mobile (evo-035)
- ✅ Bottom UI stacking fix: claw speech bubble and explore panel deferred while welcome modal is visible; sequenced appearance after dismiss (claw 1s → explore 8s) — eliminates messy overlay pile-up (evo-037)
- ✅ Single-column card layout on mobile (≤500px): 1fr grid, larger thumbnails (180px), bigger text (name 15px, owner 12px, stats 14px), more padding/gap (evo-039)
- ✅ Island bottom UI cleanup: bio panel compact pill on desktop (300px max, 10px font, 0.7 opacity), hidden on mobile; claw speech bubble repositioned higher (bottom: 100px), narrower (280px); explore panel more compact/transparent (evo-039)
- ✅ Welcome text simplified: progressive disclosure, "explore/discover/interact" instead of front-loading game mechanics (evo-043)
- ✅ Bottom HUD unified: date/weather/online as consistent pill chips with dot separators, centered flex layout (evo-043)
- ✅ Desktop welcome overlay lightened to 0.15 opacity for better island visibility (evo-043)

### ~~ISSUE-005: Visitor experience~~ ✅ COMPLETE
- ✅ Enhanced visitor welcome: shows island level, objects, visits, type, bio (evo-006)
- ✅ Login button in visitor welcome (evo-006)
- ✅ Actionable tips (steal, raid, gift) in welcome popup (evo-006)
- ✅ Browse/discover islands by category — type filter buttons in lobby (evo-008)
- ✅ "Create Your Island" CTA card for non-logged-in visitors (evo-008)
- ✅ CTA card promoted to full-width hero banner above island grid (evo-043)
- ✅ Persistent visitor info bar below topbar: island name, owner, level, type, visits (evo-011)
- ✅ "← Lobby" back link in topbar + visitor info bar for easy navigation (evo-016)
- ✅ "Explore more islands" suggestion panel for visitors on island page — 3 random picks, auto-hide (evo-017)

## 🟢 Nice to Have

### ISSUE-006: Social features — PARTIALLY DONE
- ✅ Island guestbook: visitors can leave messages per island (evo-010)
- ✅ Guestbook API with rate limiting (1 msg/IP/island/5min) (evo-010)
- ✅ Sliding panel UI with name/message form (evo-010)
- ✅ Guestbook badge: message count on 📝 button with auto-refresh (evo-011)
- ✅ Global activity feed: /api/activity endpoint + lobby UI (evo-019)
- ✅ Activity feed timestamps fixed, owner names cleaned up (evo-020)
- ✅ Share button on island pages: copy-link + Twitter intent popup (evo-021)
- ✅ OpenGraph + Twitter Card meta tags for social sharing on all pages (evo-021)
- ✅ Island leaderboard: /api/leaderboard + tabbed lobby UI with medals (evo-022)
- Friend list / follow islands

### ISSUE-011: Welcome modal background too opaque — ✅ FIXED (evo-028)
- ✅ Reduced overlay opacity from 0.88-0.92 to 0.42-0.45, blur from 4-6px to 3px (evo-028)
- Island now visible/enticing behind modals

### ISSUE-010: Card text & thumbnail readability — ✅ COMPLETE
- ✅ Empty island thumbnails: gradient ocean + mini island placeholder instead of flat dark blue (evo-027)
- ✅ Card stat row: 11→12px desktop, 12→13px mobile, color #aabbcc→#c0d4e8 (evo-027)
- ✅ Island name: 12→13px, owner name: 9→10px with better contrast (evo-027)
- ✅ Island card names: 2-line clamp wrapping instead of single-line truncation, better readability for long names (evo-032)
- ✅ Island name: color #adf→#c0e8ff, weight 600→700 for bolder/brighter appearance (evo-042)
- ✅ Owner name: color #a8bbc8→#b8ccd8 for better contrast (evo-042)
- ✅ Stats: color #c0d4e8→#d0e0f0, added text labels "visits"/"objects" (hidden on mobile) (evo-042)
- ✅ Filter/sort buttons: font 11→12px, height 36→38px, stronger active state (evo-042)
- ✅ Filter active state strengthened: background 0.35, glow 12px, text #ddeeff, inactive buttons brighter (#a0b4c8). Grid gap 14→16px. Leaderboard tabs matched. (evo-048)
- ✅ Badge system standardized: all badges 9px/6px-radius/consistent padding, NEW badges unified to #ff6b9d pink, MY tag repositioned to top-left to avoid overlap, empty overlays subtler (evo-044)
- ✅ Empty card overlays dramatically reduced: opacity 0.4→0.15, type tints 0.35→0.12, emoji larger (28px) and more visible (0.6 opacity), text 9px and readable — cards now look inviting instead of broken (evo-046)
- ✅ Card bio text: font 11→12px, color #99aabb→#b0c4d8, max-height 24→28px for better readability (evo-047)
- ✅ Owner name: color #b8ccd8→#c4d4e4 for even better contrast (evo-047)

### ISSUE-012: Loading UX — ✅ COMPLETE
- ✅ Lobby skeleton loading: shimmer card placeholders while islands fetch (evo-029)
- ✅ Island page loading screen: animated 🦞 with wave effect + progress bar, auto-hides on canvas ready (evo-029)

### ISSUE-014: Lobby visual hierarchy — PARTIALLY DONE
- ✅ Recent Activity and Leaderboard sections collapsed by default with ▸/▾ toggle arrows; island cards now visible above the fold (evo-037)
- ✅ Collapse state persisted via localStorage
- ✅ Card stats row simplified: removed date timestamp and type badge, kept ⭐ Level + visits + objects (evo-038)
- ✅ Level badge moved from card header to stats row for cleaner hierarchy (evo-038)
- ✅ Stats font bumped 12→13px desktop, gap 14→20px for better readability (evo-038)
- ✅ Mobile: hides object count, shows only Level + visits for max clarity (evo-038)
- ✅ Dual-font typography: pixel font (Press Start 2P) for headings only, Inter sans-serif for all body/metadata/stats — massive readability improvement (evo-041)
- Card text readability addressed via font system overhaul

### ISSUE-015: Island page bottom area polish — ✅ COMPLETE
- ✅ Bottom gradient reduced, explore panel compacted, status bar anchored properly (evo-041)
- ✅ Bottom HUD unified: date/weather/online as consistent pill chips with dot separators (evo-043)
- ✅ Bottom UI z-index layering fixed: explore panel (z:110) above status bar (z:100), bio pill (z:105) in between, proper spacing (bottom:52px) so no overlap (evo-044)
- ✅ Topbar consolidated for visitors: single row with island name + owner, hidden owner-only buttons/badges, removed redundant visitor-info-bar (evo-046)
- ✅ Bottom UI readability: explore panel more opaque (0.92), removed backdrop-filter blur (visual noise), brighter card links (#e8f0ff), taller (88px). Bio pill more opaque (0.95), 11px font. Claw speech repositioned (140px). Bottom HUD subtle top border separator. (evo-047)
- ✅ Welcome modal text contrast: stats 12px/#a0b8cc, description 13px/#b0d4f0, login link 11px/#7cc8ff with underline, stronger modal shadow, brighter placeholders/labels (evo-048)

### ISSUE-020: Lobby hero stats readability — ✅ FIXED (evo-049)
- ✅ Hero stats font 11→13px, color #aabbcc→#c8d8e8 (brighter, better contrast)
- ✅ Added subtle pill background (rgba(100,180,255,0.06)) with rounded border for visual separation
- ✅ Letter-spacing 0.3px for improved scanability
- ✅ Online count 10→12px with more vertical margin
- AI had rated lobby readability at 5/10, primarily due to tiny/invisible hero stats

### ISSUE-021: Island bottom UI stacking — ✅ FIXED (evo-049)
- ✅ Claw speech bubble repositioned higher: bottom 140→190px (desktop), 70→90px (mobile)
- ✅ Added z-index:100 to claw speech (below explore panel z:110) for proper layering
- ✅ Explore panel padding increased for breathing room
- AI had rated island usability at 5/10 due to speech bubble overlapping explore panel

### ISSUE-016: Lobby CTA placement optimization — ✅ FIXED (evo-058)
- ✅ CTA card converted to full-width banner (evo-043)
- ✅ Fixed CTA duplication: banner title "Create Your Island" → "Your Island Awaits" (inviting headline), single CTA button "🦞 Create Your Island" (evo-058)
- ✅ Banner no longer clickable — only the button triggers action (removed hover transform/cursor on banner div) (evo-058)
- AI confirmed: title is inviting and distinct from CTA, single clear action

### ISSUE-017: Hero stats pluralization grammar — ✅ FIXED (evo-045)
- ✅ Fixed "1 fisheries" → "1 fishery", all stats now handle singular/plural correctly (evo-045)

### ISSUE-018: Daily Report bulletin bar shown to visitors — ✅ FIXED (evo-045)
- ✅ Bulletin bar (farm stats, theft reports) now hidden for non-owners — visitors see clean island view (evo-045)
- Reclaims vertical space for game content, reduces UI chrome-to-content ratio

### ISSUE-019: Island topbar consolidation for visitors — ✅ COMPLETE
- ✅ Visitor-info-bar hidden globally (was mobile-only) — no more redundant second row (evo-046)
- ✅ Owner-only topbar items (level/type badges, coin count, Bag/Shop/Land/Guestbook/Share/Lobby buttons) hidden for visitors via `body:not(.owner-view)` CSS (evo-046)
- ✅ Topbar `#hud-name` shows island name + owner for visitors: `🏝️ Test by 🦞 Eric J` (evo-046)
- ✅ Visitor topbar is now a single clean row: island name · ← Lobby · Visiting · Log in (evo-046)

### ISSUE-023: Lobby card metadata readability — ✅ FIXED (evo-053)
**Found:** AI Visual Analysis rated lobby readability 5/10 (mobile), 6/10 (desktop)
**Problem:** Card stats (visits, objects, level), bio text, and owner names too small and low-contrast. Metadata hard to scan on mobile.
**Fix:**
- [x] Stats font 13→14px desktop, 14→15px mobile (≤500px single-column)
- [x] Stats color bumped to #d8e8f5 for better contrast
- [x] Level badge (⭐ Lv.N) bolder weight
- [x] Subtle stats row background pill (rgba(100,180,255,0.05), 8px radius)
- [x] Card bio: 12→13px, color #b0c4d8→#bdd0e4, line-height 1.3→1.4
- [x] Owner name: #c4d4e4→#d0dce8
- [x] Search input: ensured 40px+ height, 14px+ font

### ISSUE-024: Welcome Modal CTA Clarity + Onboarding — ✅ FIXED (evo-054, refined evo-057)
**Found:** AI Visual Analysis rated first-time user experience 5/10
**Problem:** "Start Exploring!" CTA was vague, guestbook fields gated entry, no onboarding hints about controls.
**Fix:**
- [x] CTA renamed "👁 Start Exploring!" → "🏝️ Enter Island" → "🎮 Start Exploring" (evo-057) — clearest action intent
- [x] Guestbook fields collapsed by default on ALL viewports (not just mobile) — "Leave a message ✎" toggle visible
- [x] Added onboarding hint text: "Click/tap to move around • Interact with objects • Discover secrets"
- [x] Entry feels instant — guestbook is optional, not a gate
- [x] Welcome modal/sheet dismissable by tapping outside (overlay click handler) (evo-057)
- [x] Mobile bottom sheet compacted: max-height 30vh→25vh, tighter padding (evo-057)
- [x] AI rated visitor experience 8/10 (desktop) after evo-057 changes

### ISSUE-025: Mobile Filter Bar Horizontal Scroll — ✅ FIXED (evo-054)
**Found:** AI Visual Analysis rated mobile friendliness 5/10
**Problem:** Sort+filter buttons wrapped on mobile, creating multiple rows that pushed island cards down.
**Fix:**
- [x] Filter bar row (sort + type filter) now horizontally scrollable on ≤600px
- [x] `overflow-x:auto`, hidden scrollbar, `flex:0 0 auto` buttons (no stretch)
- [x] Search input moved to separate full-width row below filter chips
- [x] Touch targets maintained (44px min-height)

### ISSUE-026: Lobby Discovery Path — ✅ FIXED (evo-055)
**Found:** AI Visual Analysis (evo-054)
**Problem:** AI rated overall lobby UX 6/10. Page feels like a long catalogue with weak guidance. No strong primary discovery action above the fold.
**Fix:**
- [x] CTA button renamed "Get Started" → "Create Your Island" — clearer action intent
- [x] Added "🎲 Random Island" discovery pill button below CTA banner
- [x] Random button picks a random island card and navigates to it — instant exploration
- [x] Mobile responsive (smaller font/padding on ≤600px)

### ISSUE-027: Island Welcome Modal — Clarify "12 objects" — ✅ FIXED (evo-055)
**Found:** AI Visual Analysis (evo-054)
**Problem:** "12 objects" stat is unclear to first-time visitors. What does it mean?
**Fix:**
- [x] Changed "objects" → "items" throughout visitor-facing UI (topbar stats, welcome modal)
- [x] Claw speech bubble: "things to discover" → "buildings & items to discover"
- [x] Welcome modal hint text: "Interact with objects" → "Click buildings to interact • Drag to move around"
- [x] Tooltip updated: "Objects placed" → "Buildings & items on this island"

### ISSUE-028: Interactive Object Affordances — ✅ FIXED (evo-056)
**Found:** AI Visual Analysis (evo-055) — rated first-time visitor experience 6/10
**Problem:** Visitors don't know which objects are interactive vs decorative. No visual distinction between clickable buildings and background elements.
**Fix:**
- [x] After welcome modal dismissed, interactive objects pulse with subtle blue glow for 8 seconds
- [x] Floating hint text "✨ Click the glowing buildings!" (desktop) / "✨ Tap the glowing spots!" (mobile) shown for 3s
- [x] Canvas overlay pass draws translucent blue circles behind objects with click handlers
- [x] Auto-fades after 8s with smooth opacity transition
- [x] Only shown to visitors (`!isOwner`), not island owners

### ISSUE-030: Mobile Touch Terminology — ✅ FIXED (evo-056)
**Found:** AI Visual Analysis (evo-056) — rated mobile usability 4/10
**Problem:** Onboarding hints used desktop-only language ("Click buildings", "Drag to move") on touch devices.
**Fix:**
- [x] Touch device detection via `'ontouchstart' in window || navigator.maxTouchPoints > 0`
- [x] Mobile: "Tap buildings to interact • Swipe to explore • Discover secrets"
- [x] Desktop: "Click buildings to interact • Drag to move around • Discover secrets"
- [x] Claw tip messages also responsive: "Swipe to pan, pinch to zoom" (touch) vs "Drag to pan, scroll to zoom" (mouse)

### ISSUE-029: Island Bottom UI Consolidation — ✅ PARTIALLY FIXED (evo-059)
**Found:** AI Visual Analysis (evo-055) — rated bottom UI 6/10
**Problem:** Speech bubble, explore panel, bio tooltip, and status bar are four separate overlays competing at the bottom.
**Fix (evo-059):**
- [x] Bio tooltip removed entirely for visitors (duplicated claw speech content)
- [x] Claw speech auto-fades after 6s and hides (was persistent until manual dismiss)
- [x] After claw fades, explore panel is fully visible and unobstructed
- [x] Only 2 bottom elements remain: explore panel + status bar (clean hierarchy)
**Remaining:** Could still consolidate explore panel + status bar into a single dock, but clutter is significantly reduced.

### ISSUE-035: Mobile Welcome Overlay Too Intrusive — ✅ FIXED (evo-059)
**Found:** AI Visual Analysis (evo-059) — rated mobile overlay intrusiveness 4/10
**Problem:** Welcome bottom sheet covered too much of the island on mobile, blocking visibility.
**Fix:**
- [x] Welcome sheet auto-minimizes to compact single-line CTA bar after 4s on mobile (≤600px)
- [x] Minimized state: only "🎮 Start Exploring" button visible, ~52px height
- [x] Expand chevron (▲) to restore full content if user wants to read
- [x] Auto-dismiss timer skipped when minimized — user controls dismissal
- [x] Desktop behavior unchanged

### ISSUE-031: Lobby Sticky Filter Bar — ✅ FIXED (evo-057)
**Found:** AI Visual Analysis (evo-057) — rated lobby clarity 6/10
**Problem:** Filter/search controls scroll away when browsing islands. Users must scroll back up to change filters.
**Fix:**
- [x] Filter section (sort buttons + type filters + search) now `position: sticky; top: 0; z-index: 50`
- [x] Dark semi-transparent background with backdrop blur when stuck
- [x] Subtle bottom border/shadow for visual separation
- [x] Mobile compact padding (~50-60px height when stuck)
- [x] CTA banner and hero section scroll away naturally above the sticky point

### ISSUE-032: Lobby Above-Fold Simplification — ✅ FIXED (evo-062, evo-101)
**Found:** AI Visual Analysis (evo-057) — rated first-time clarity 6/10
**Problem:** Too much content before island cards: hero, activity, leaderboard (collapsed but visible), "Islands (31)" heading, filter bar, CTA, Random Island. AI suggests collapsing filters into a drawer or reducing sections.
**Fix (evo-062):**
- [x] Replaced wordy subtitle ("a universe of tiny islands — build yours, visit others") with 3-step visual onboarding strip: 🏝️ Create → 🏗️ Build → 🌍 Explore
- [x] Mobile responsive (smaller icons/text on ≤600px)
- [x] AI rated first-time clarity 6/10 → 8/10 after change
**Remaining:** ~~Consider hiding "Islands (31)" section title on mobile, integrating CTA into hero area.~~ ✅ Done (evo-101): section heading hidden, hero/CTA/filters compacted on mobile.

### ISSUE-034: Island Bio Toast Deferred Behind Welcome Modal — ✅ FIXED (evo-058)
**Found:** AI Visual Analysis (evo-058) — rated island visibility 4/10
**Problem:** Bio toast at bottom-left duplicated welcome modal content ("A farm island with 12 objects...") while modal was open, adding redundancy and visual noise.
**Fix:**
- [x] `loadIslandStory()` checks if welcome modal is visible — stores data in `window._pendingBioData` instead of showing
- [x] `closeVisitorWelcome()` shows deferred bio toast after modal dismissed (8s instead of 10s)
- [x] Eliminates content duplication during onboarding flow

### ISSUE-033: Island Welcome Modal Still Text-Heavy — ✅ FIXED (evo-062)
**Found:** AI Visual Analysis (evo-057) — rated desktop visitor experience 8/10 but noted "slightly text-heavy"
**Problem:** Welcome modal shows title, owner, type tag, stats, description, exploration text, guestbook link, onboarding hints, CTA, and login link. Could be simplified.
**Fix (evo-062):**
- [x] Removed description paragraph (`vw-desc-text`) — duplicated bio/claw speech content
- [x] Moved guestbook toggle below CTA button (was competing above it) with reduced opacity
- [x] CTA button enhanced: gradient background, font-weight 600, box-shadow glow — clear primary action
- [x] CTA hierarchy now clear: primary "Start Exploring" → secondary "or log in" → tertiary "Leave a message"

### ISSUE-007: Performance — PARTIALLY ADDRESSED (evo-100)
- Lobby thumbnail generation is per-request — add caching
- Large worlds with many objects load slowly

### ~~ISSUE-009: E2E Test Coverage~~ ✅ COMPLETE (18/18 tests)
- ✅ Island page test now waits for canvas render (not just domcontentloaded) (evo-014)
- ✅ New test: island_no_console_errors (evo-014)
- ✅ New test: guestbook_api — POST + GET guestbook with rate limit handling (evo-016)
- ✅ New test: lobby_search_filter — search input filters cards correctly (evo-016)
- ✅ New test: lobby_type_filter — type filter buttons work correctly (evo-016)
- 18/18 tests passing
- ✅ Test resilience: safe_context() auto-relaunches browser on crash, --disable-dev-shm-usage (evo-036)
- ✅ Activity feed API test: validates endpoint, response shape, event fields (evo-020)
- ✅ Login flow test: verifies form opens, email input + send code button present (evo-017)
- ✅ Mobile island viewport test: 375x667 canvas renders, topbar fits, no console errors (evo-017)
- ✅ Leaderboard API test: validates endpoint, categories, leader fields (evo-023)
- ✅ Leaderboard lobby UI test: verifies section + tab buttons render (evo-023)
- Need: end-to-end login with verification code (requires test email setup)

### ~~ISSUE-008: Visual polish~~ ✅ COMPLETE
- ✅ Thumbnail brightness normalization: brightness(1.1) contrast(1.05) filter + bottom gradient overlay (evo-018)
- ✅ Island name size bump 11→12px, owner name secondary styling (evo-018)
- ✅ Type filter buttons now labeled: 🌾 Farm, 🐟 Fish, ⛏️ Mine, 🌲 Forest (evo-018)
- ✅ Filter label bolder and more visible (evo-018)
- ~~Island card thumbnails could be higher quality~~ — addressed via brightness normalization (evo-018)
- ✅ Lobby card hover: lift, glow, border brightening (evo-006)
- ✅ Floating header emoji animation (evo-006)
- ✅ Thumbnail scale-on-hover effect (evo-006)
- ✅ Staggered card entrance fade-in animation (evo-007)
- ✅ Enhanced hover with scale + glow (evo-007)
- ✅ Auto-generated bio fallback for all islands (evo-007)
- ✅ "✨ New" badge for unvisited islands (evo-007)
- ✅ Better empty state for new islands — CSS overlay with type emoji + "No objects yet" (evo-012)
- ✅ Lobby sections: Active Islands / New Islands split for better discoverability (evo-012)
- ✅ Enhanced search box with focus glow effect (evo-008)
- ✅ "End of universe" footer for island grid (evo-008)
- ✅ Stronger section separation: 14px titles, blue accent border, gradient bg, glow divider (evo-015)
- ✅ Filter bar consistency: uniform 36px height, background containers, "Filter" label (evo-015)
- ✅ Card metadata readability: 10px stats, brighter colors (#99b), hero stats bump (evo-015)
- ✅ Empty island cards: varied tip messages (10 rotating), type-tinted overlays, "Visit →" hint (evo-017)
- ✅ Compact New Islands section: shorter thumbnails (100px), "✨ Just created" badge (evo-017)
- ✅ Card height consistency: flexbox layout with stats pushed to bottom via margin-top:auto (evo-020)
- ✅ Activity feed readability: font 9→11px, better contrast, backdrop blur, section title polish (evo-021)
- ✅ Island welcome modal: close ✕ button, field labels, improved placeholder contrast (evo-021)

### ISSUE-036: Filter Bar Sort/Type Confusion — ✅ FIXED (evo-060)
**Found:** AI Visual Analysis (evo-060) — rated filter clarity 7/10
**Problem:** Sort buttons (Popular/Recent/Random) and type filters (All/Farm/Fish/Mine/Forest) used identical styling and sat in one undifferentiated row. Both "Popular" and "All" appeared active simultaneously, confusing users about what controls what.
**Fix:**
- [x] Added "Sort:" and "Type:" group labels (10px, muted color #6688aa)
- [x] Vertical divider between sort and type groups
- [x] Type filters use separate `.type-btn` class with distinct active styling (teal/cyan tint instead of blue)
- [x] "Random" button restyled as ghost/outlined action button (not a toggle) — clearly an action, not a sort mode
- [x] Mobile horizontal scroll preserved

### ISSUE-037: Island Cards Missing Type Identification — ✅ FIXED (evo-060)
**Found:** AI Visual Analysis (evo-060) — cards lack type at-a-glance
**Problem:** Island cards showed no island type indicator. Users had to read the bio text or use filters to discover type.
**Fix:**
- [x] Color-coded type badge in stats row: 🌾 Farm (green), 🐟 Fish (blue), ⛏️ Mine (amber), 🌲 Forest (dark green)
- [x] Badges have colored left border + tinted background matching type
- [x] 10px font, subtle but readable, consistent with dark theme
- [x] Hidden in compact New Islands cards (`.compact-new .type-badge { display: none }`)
- [x] Mobile responsive (9px font on smaller screens)

### ISSUE-038: Explore Panel Too Dim/Low-Contrast — ✅ FIXED (evo-061)
**Found:** AI Visual Analysis (evo-061) — rated as #1 island page issue
**Problem:** "Explore more islands" panel was too faint — text dim, links low-contrast, panel blended into dark background. Hurt discoverability of island browsing (a core action).
**Fix:**
- [x] Panel title: 11→13px, bold, color #f0f4ff (near-white)
- [x] Island name links: 12→13px, font-weight 600, color #ffffff
- [x] Owner text: #6688aa→#90b0cc (significantly brighter)
- [x] Stats/visits text: #557→#90b0cc (brighter)
- [x] Top border accent: 1px→2px, rgba(100,180,255,0.4) for visual pop
- [x] Panel background: slightly lighter rgba(12,22,38,0.95) + inner glow
- [x] Panel height: 88→96px, padding: 10px 14px→12px 16px
- [x] Close button: brighter (#a0b8d0, bold)

### ISSUE-039: Duplicate Random Button Actions — ✅ FIXED (evo-061)
**Found:** AI Visual Analysis (evo-061) — flagged as confusing UX
**Problem:** Two separate "Random" buttons: ghost button in filter bar (evo-060) AND "🎲 Random Island" pill below CTA banner (evo-055). Duplicative actions confused intent.
**Fix:**
- [x] Removed standalone Random Island pill below CTA banner
- [x] Filter bar Random button upgraded: dashed→solid border (more confident/visible)
- [x] Single random action point in sticky filter bar — always accessible

### ISSUE-040: Card Bio Text Truncation — ✅ FIXED (evo-063)
**Found:** AI Visual Analysis (evo-063) — rated card readability 5/10
**Problem:** Card bio descriptions truncated mid-word ("Come v...", "just getting starte...") due to single-line nowrap CSS. Looked broken and added no value.
**Fix:**
- [x] Changed `.card-bio` from `white-space: nowrap` to 2-line clamp (`-webkit-line-clamp: 2`)
- [x] Increased `max-height` to accommodate 2 lines of text
- [x] Bios now show full or near-full text with proper ellipsis at end of line 2
- [x] Mobile (≤500px) and compact New Islands sections still hide bio (unchanged)

### ISSUE-041: Explore Panel Still Nearly Invisible — ✅ FIXED (evo-063, redesigned evo-067)
**Found:** AI Visual Analysis (evo-063) — rated #1 island page issue despite evo-061 fixes
**Problem:** "Explore more islands" panel still blends into dark ocean background. Text dim, panel indistinguishable.
**Fix (evo-063):**
- [x] Background lightened/blued: rgba(16,30,52,0.97)
- [x] Full border added (not just top): 1px solid rgba(100,180,255,0.25) + 2px top accent
- [x] Stronger glow shadow with blue tint
- [x] Header text bumped to 14px bold near-white (#f8faff)
- [x] Owner/stats text brightened (#a8c8e0)
- [x] Panel height increased to 110px
- [x] Close button made more visible
**Redesign (evo-067):**
- [x] Converted from flat text list to mini-cards with island thumbnails (50x40px)
- [x] Each card: thumbnail + island name (bold, white, with → arrow) + owner + stats
- [x] Cards in horizontal flex row with 8px gap
- [x] Card hover: lift + brighter border + blue glow
- [x] Panel now unmistakably interactive — AI had rated bottom panel 3/10, this addresses it

### ISSUE-042: Welcome Modal Blocks Island View on Desktop — ✅ FIXED (evo-064)
**Found:** AI Visual Analysis (evo-064) — rated island visibility 5/10 on both desktop and mobile
**Problem:** Welcome modal showed redundant stats (Lv/items/visits) already visible in topbar. Emoji icon and large padding wasted space. Modal max-width 400px blocked too much island.
**Fix:**
- [x] `#vw-island-stats` hidden on all viewports (topbar already shows this info)
- [x] `#vw-island-emoji` hidden on all viewports (unnecessary when island is visible behind)
- [x] Modal padding reduced: 28px 32px → 20px 28px
- [x] Modal max-width reduced: 400px → 360px
- [x] Bio section compacted: max-height 60px → 40px, font-size 10px
- Result: Modal ~30% smaller, more island visible behind it

### ISSUE-043: Lobby Card Stats Row Readability — ✅ FIXED (evo-064)
**Found:** AI Visual Analysis (evo-064) — rated card readability 6/10
**Problem:** Type badges (Farm/Fish/Mine/Forest) too small at 10px. Stats row lacked consistent touch targets. Level badge not bold enough to stand out.
**Fix:**
- [x] Type badge font: 10px → 11px with font-weight 600
- [x] Stats row: min-height 36px + align-items center for consistent touch targets
- [x] Level badge: added `.stat-level` class with font-weight 700
- [x] Mobile stats color: #d8e8f5 → #e0eef8 for better contrast
- [x] Mobile owner name: 11px → 12px for single-column readability

### ISSUE-044: Lobby Featured Section Polish — ✅ FIXED (evo-067)
**Found:** AI Visual Analysis (evo-066) — rated Featured section 5/10
**Problem:** Featured cards don't explain *why* they're featured. Thumbnails similar to regular cards, no editorial hook.
**Fix:**
- [x] Added reason tags to featured cards: "🏆 Most Visited", "⭐ Highest Level", "🏗️ Most Built"
- [x] Reason determined by each island's top distinguishing stat
- [x] Styled as colored pill chips (gold/blue/green) below card stats
- [x] Subtle, doesn't compete with island name

### ISSUE-045: Welcome Toast Visibility — Working as Designed
**Found:** evo-066 — toast auto-dismisses at 8s (desktop) / 6s (mobile)
**Status:** Working as designed. Toast is brief and non-blocking. The island is now fully visible without overlay.
**Note:** If users miss the toast, the claw speech bubble and onboarding hints provide fallback guidance.

### ISSUE-046: Mobile Island Camera Zoom — ✅ FIXED (evo-069)
**Found:** AI Visual Analysis (evo-069) — rated mobile island visibility 6/10
**Problem:** Island appeared too small on mobile (390px), with excessive blue grid/ocean visible around it. Buildings and objects were hard to recognize.
**Fix:**
- [x] Camera zoom boosted 30% on mobile (≤500px), 15% on tablet (≤768px)
- [x] Max zoom cap increased 2.0→2.5 for small islands
- [x] Vertical centering adjusted for mobile (0.42→0.40) to accommodate topbar
- [x] Island now fills ~80-90% of mobile viewport width instead of ~55-60%

### ISSUE-047: Claw Speech Bubble Lacks CTA for Visitors — ✅ FIXED (evo-069)
**Found:** AI Visual Analysis (evo-069) — rated speech bubble actionability 6/10
**Problem:** Speech bubble showed welcome text but had no call-to-action. Visitors didn't know what to do next. The only interactive element was a tiny ✕ close button.
**Fix:**
- [x] Added "🎮 Explore" button (primary, blue gradient) — dismisses bubble to let user explore
- [x] Added "📝 Guestbook" button (secondary, outline) — opens guestbook panel
- [x] Auto-fade timer extended from 6s→10s for visitors to give time to click CTAs
- [x] Buttons styled consistently with game theme (monospace, blue tones)
- [x] Owner-only: no CTA buttons shown (owners see existing behavior)

### ISSUE-048: Harvest Badge "6 ready!" Visible to Visitors — ✅ FIXED (evo-070)
**Found:** AI Visual Analysis (evo-070) — rated owner info leak 8/10 concern
**Problem:** The golden "🥬 6 ready!" harvest badge and mini crop icons rendered on the island canvas near the farm/barn building were shown to ALL users, including visitors. Visitors can't harvest crops, so this is misleading owner-only information.
**Fix:**
- [x] Wrapped crop status rendering block (mini crop icons + "ready!" badge) in `isOwner` check
- [x] Visitors now see clean farm building without harvest indicators

### ISSUE-049: Explore Panel Auto-Hides After 15s — Dead-End Screen — ✅ FIXED (evo-070)
**Found:** AI Visual Analysis (evo-070) — rated post-onboarding guidance 2/10
**Problem:** After the welcome toast and claw speech bubble dismiss, the Explore More Islands panel also auto-hid after 15 seconds. Visitors were left on a static dead-end screen with no navigation, no CTAs, and no way to discover other islands.
**Fix:**
- [x] Removed auto-hide timeout — panel persists until manually closed
- [x] Added collapse/minimize toggle (▼/▲) next to close button — minimizes to header bar only
- [x] Panel opacity slightly reduced (0.95) since it's now persistent
- [x] Close ✕ still fully removes panel
- [x] Visitors always have navigation available to other islands

### ISSUE-050: Lobby Visual Hierarchy — Above-Fold Compaction — ✅ FIXED (evo-071)
**Found:** AI Visual Analysis (evo-071) — rated visual hierarchy 6/10
**Problem:** Hero section, CTA banner, filter bar, and section titles consumed too much vertical space. Island cards (the core content) were pushed too far below the fold. ~80px of unnecessary padding/margin.
**Fix:**
- [x] Hero padding reduced: 40px 0 30px → 24px 0 16px
- [x] Hero h1 margin-bottom: 8px → 4px
- [x] Onboarding steps margin: 12px auto 20px → 8px auto 12px
- [x] CTA banner padding: 18px 28px → 12px 20px, margin-bottom: 20px → 12px
- [x] CTA banner title font: 15px → 14px, button padding reduced ~20%
- [x] Section title margin: 30px 0 14px → 20px 0 12px
- [x] Hero stats padding/margin compacted
- [x] Mobile overrides also tightened
- [x] ~60-80px of vertical space saved — island cards appear significantly higher

### ISSUE-051: Explore Panel Invisible on Initial Visit — ✅ FIXED (evo-071, refined evo-072)
**Found:** AI Visual Analysis (evo-071) — rated bottom panel visibility 2/10
**Problem:** Explore More Islands panel was deferred behind welcome toast + claw speech bubble chain. Total delay: 8-15+ seconds. Most visitors never saw it. The deferral was unnecessary since the panel sits at the bottom and doesn't overlap with the top-positioned welcome toast.
**Fix (evo-071):**
- [x] Removed deferral logic in `loadExploreMore()` that waited for welcome modal and claw speech to hide
- [x] Removed deferred explore panel handler in `closeVisitorWelcome()`
- [x] Panel now loads 3 seconds after page load regardless of welcome toast state
- [x] Bottom panel is immediately available for navigation to other islands
**Refinement (evo-072):**
- [x] Claw speech auto-fade reduced 10s→6s for visitors — speech was blocking explore panel too long
- [x] Explore panel intelligently deferred: if claw speech is visible at 3s, waits until speech fades (6s) then shows 1s later (~7.5s total)
- [x] Early dismiss (✕, Explore, Guestbook buttons) triggers explore panel 1s after dismiss
- [x] `_clawSpeechVisible` / `_showExplorePending` coordination flags prevent simultaneous display
- [x] Pulsing blue glow border animation on explore panel appearance (2 pulses over 3s) draws attention
- [x] AI re-rated: clean sequenced flow, no overlapping elements, panel clearly visible after speech fades

### ISSUE-052: Lobby Cards Missing "Visit" Action Affordance — ✅ FIXED (evo-072)
**Found:** AI Visual Analysis (evo-072) — rated first-time clarity 6.5/10
**Problem:** Island cards had no visible call-to-action. Users didn't know clicking a card takes them to the island. Featured cards had "Visit →" but regular Active Islands and New Islands cards had no indication of what would happen when clicked.
**Fix:**
- [x] CSS `::before` pseudo-element on `.island-card .thumb` shows "Visit →" dark overlay on hover
- [x] `@media (hover: hover)` ensures overlay only activates on hover-capable devices
- [x] Smooth 0.25s opacity transition, pointer-events:none (doesn't block existing onclick)
- [x] Mobile (≤600px): permanent subtle "Visit →" pill at bottom-right of thumbnail (opacity 0.75)
- [x] Consistent with Featured card "Visit →" button styling

### ISSUE-053: Mobile Card Stats Simplified — ✅ FIXED (evo-073)
**Found:** AI Visual Analysis (evo-073) — rated mobile card readability 5/10
**Problem:** Stats row on mobile cards had 4 elements competing: level badge, type badge, visits, objects. Too dense for quick scanning.
**Fix:**
- [x] Type badge (Farm/Fish/Mine/Forest) hidden on mobile ≤500px
- [x] Objects count (🧱 N) hidden on mobile ≤500px
- [x] Stats font-weight bumped to 600 on mobile for better legibility
- [x] Mobile cards now show only Level + Visits — clean and scannable

### ISSUE-054: Island Visitor Topbar Simplified — ✅ FIXED (evo-073)
**Found:** AI Visual Analysis (evo-073) — rated info hierarchy 5/10 (mobile), 6/10 (desktop)
**Problem:** Too many competing header items: island name, inline stats, "👁 Visiting · Log in" badge — all fighting for attention. "Visiting" label was redundant.
**Fix:**
- [x] Removed "👁 Visiting ·" prefix — visitors just see "🔑 Log in" or "🏝 My Island"
- [x] Badge styling simplified (removed heavy background/border on mobile)
- [x] Visitor stats (#hud-visitor-stats) fully hidden on mobile ≤600px (shown in welcome toast instead)
- [x] Topbar feels cleaner with fewer competing elements

### ISSUE-055: Explore Panel Card Readability — ✅ FIXED (evo-074)
**Found:** AI Visual Analysis (evo-074) — rated explore/discover 2/10 on island page
**Problem:** Explore More Islands panel mini-cards had names truncated at 12 chars (most names cut off), cards too narrow (max 165px), stats text dim (#98ccec), no "All Islands" link for full lobby access.
**Fix:**
- [x] Name truncation limit increased 12→18 chars, owner limit 10→14 chars
- [x] Card dimensions: min-width 148→160px, max-width 165→200px
- [x] Thumbnail size increased 50x40→56x44px
- [x] Stats text brightened #98ccec→#b0d8f0, border visibility 0.35→0.45
- [x] Added "← All Islands" lobby link in panel header for full directory access

### ISSUE-056: Lobby Above-Fold Content Density — ✅ FIXED (evo-074)
**Found:** AI Visual Analysis (evo-074) — rated above-fold 6/10
**Problem:** Hero + CTA banner + filter bar pushed island cards too far down the page. ~60px of unnecessary vertical spacing across hero padding, onboarding steps margins, CTA banner, and section titles.
**Fix:**
- [x] Hero padding reduced: 24px 0 16px → 14px 0 6px
- [x] Hero h1 margin-bottom: 4px → 2px
- [x] Onboarding steps margin: 8px auto 12px → 4px auto 6px
- [x] CTA banner: min-height auto, padding 12→10px, margin-bottom 12→8px
- [x] CTA banner subtitle hidden (display:none) — redundant with onboarding steps
- [x] Section title margins compacted: 20px 0 12px → 12px 0 10px
- [x] Featured section top margin: added 8px (was inheriting larger value)
- [x] Featured scroll padding bottom: 12→8px
- [x] Leaderboard and filter bar margins reduced
- [x] ~70px total vertical space saved — island cards visible significantly higher

### ISSUE-057: Island Page Visitor Navigation — ✅ FIXED (evo-075)
**Found:** AI Visual Analysis (evo-075) — rated navigation 3/10
**Problem:** Visitors on an island page had no obvious way to browse other islands. The "← Lobby" topbar link was small and easily missed. The Explore More Islands panel at the bottom only appears after 7+ seconds (deferred behind welcome flow). No primary nav entry for island discovery.
**Fix:**
- [x] Added "🌏 Explore" button in topbar right side (mode-btns area)
- [x] Visitor-only: shown via `body:not(.owner-view)` CSS, hidden for owners
- [x] Links to `/` (lobby page) for immediate island discovery
- [x] Mobile responsive: emoji-only on ≤600px to save space
- [x] AI re-rated navigation discoverability: 3/10 → 8/10

### ISSUE-058: Desktop Card Stats Row Readability — ✅ FIXED (evo-075)
**Found:** AI Visual Analysis (evo-075) — rated card readability 6/10
**Problem:** Card stats row had competing small elements (level, type badge, visits, objects). Bio text and owner names lacked visual hierarchy. Stats row was hard to scan quickly.
**Fix:**
- [x] Desktop stats bumped to 14px / font-weight 600 (was 13px / normal)
- [x] Separator dots (·) between stat items for cleaner scanning
- [x] Stats row gap reduced 14→4px (dots provide visual separation)
- [x] Bio text opacity reduced to 0.75 — clearly secondary to name/stats
- [x] Owner name "by" prefix added on desktop (hidden ≤500px)
- [x] AI re-rated card readability: 6/10 → 7/10

### ISSUE-059: Claw Speech Bubble Blocks Explore Panel — ✅ FIXED (evo-076)
**Found:** AI Visual Analysis (evo-076) — rated claw speech 5/10, explore panel 4/10
**Problem:** Centered speech bubble overlay blocked the "Explore More Islands" panel, creating a congested lower third. Visitors couldn't see island navigation while the welcome message was displayed.
**Fix:**
- [x] Converted speech bubble from centered overlay to compact bottom-right corner toast
- [x] Max-width reduced to ~260px, positioned fixed at bottom-right (above explore panel)
- [x] Explore panel fully visible even while speech bubble is shown — no overlap
- [x] Auto-fade after 6s for visitors, dismissible via X, `_clawSpeechVisible` coordination preserved
- [x] AI re-rated: island visibility improved, bottom UI no longer congested

### ISSUE-060: Lobby Hero CTA Not Prominent Enough — ✅ FIXED (evo-076)
**Found:** AI Visual Analysis (evo-076) — rated CTA effectiveness 6/10, above-fold 5/10
**Problem:** "Create Your Island" button didn't stand out as the dominant hero element. Too much competing visual weight from stats, onboarding strip, and filters pushed island cards below the fold.
**Fix:**
- [x] CTA button: larger (16px font, 14px 32px padding), bright blue/cyan gradient, 2s pulsing glow animation
- [x] Stats line compacted: merged online count into stats row, reduced to 10px, tighter margins
- [x] Onboarding strip compacted: icons 20→16px, text 10→9px, reduced vertical margins
- [x] ~25-30px of vertical space saved — Featured cards render noticeably higher

### ISSUE-061: Explore Panel Card Size + Readability — ✅ FIXED (evo-077)
**Found:** AI Visual Analysis (evo-077) — rated explore/discover panel 3/10 on island page
**Problem:** Explore More Islands panel mini-cards had tiny thumbnails (56x44px) and small text (12px name, 10px owner/stats). Cards were hard to read and didn't feel clickable enough.
**Fix:**
- [x] Thumbnails enlarged: 56x44→72x56px with border definition
- [x] Text sizes bumped: name 12→13px, owner 10→11px, stats 10→11px
- [x] Card padding increased: 10px 12px→12px 14px, panel min-height 110→120px
- [x] "← All Islands" link has subtle shimmer animation on first appearance (3s, once)
- [x] Mobile responsive: 64x48px thumbnails, 12px/10px text on ≤600px

### ISSUE-062: Lobby Card Stats Order + Consolidation — ✅ FIXED (evo-077)
**Found:** AI Visual Analysis (evo-077) — rated card readability 6/10 on desktop
**Problem:** Stats row had 4 competing elements (level, type, visits, objects) with too much gap. Type badge appeared after level badge, but type provides better context-first identification.
**Fix:**
- [x] Reordered stats: Type → Level → Visits → Objects (type provides context, level shows depth)
- [x] Stats gap reduced: 20px→14px on desktop (dot separators provide visual separation)
- [x] Stats row padding increased: 4px 8px→5px 10px, border-radius 8px→10px
- [x] `.stat-label` class added with opacity 0.6 for dimmer secondary text labels
- [x] Owner name `by` prefix dimmed (opacity 0.5) to not compete with actual name

### ISSUE-063: Island Bottom Panel Confused with Status Bar — ✅ FIXED (evo-078)
**Found:** AI Visual Analysis (evo-078) — rated bottom panel readability 3/10
**Problem:** Explore More Islands panel sat directly above the bottom HUD status chips (date/weather/online). AI literally couldn't distinguish the navigation panel from status info — rated them as indistinguishable small pill elements.
**Fix:**
- [x] Hidden `#bottom-hud-chips` for visitors via `body:not(.owner-view)` CSS — visitors don't need date/weather/online info
- [x] Explore panel repositioned to bottom:0 (was bottom:36px) since status bar no longer takes space
- [x] Integrated online player count into explore panel header: "🏝️ Explore More Islands · N online"
- [x] Stronger top border accent: 3px→4px, rgba opacity 0.6→0.8
- [x] Panel min-height increased 110→120px for better visual weight

### ISSUE-064: Competing Navigation Actions on Island Page — ✅ FIXED (evo-078)
**Found:** AI Visual Analysis (evo-078) — rated navigation clarity 5/10
**Problem:** Four navigation elements serving overlapping purposes: "← Lobby" (topbar), "🌏 Explore" button, claw speech "Start Exploring", and explore panel "← All Islands". Confusing for first-time visitors.
**Fix:**
- [x] Topbar back link simplified to just "←" on all viewports (was "← Lobby" on desktop)
- [x] "🌏 Explore" button renamed to "🏝️ Islands" — shorter, clearer, doesn't compete with speech bubble
- [x] Claw speech "🎮 Explore" CTA button renamed to "👋 Got it" — dismiss-only, no navigation duplication
- [x] Explore panel "← All Islands" changed to "View All →" — forward-looking discovery language

### ISSUE-065: Explore Panel Invisible Despite Fixes — ✅ FIXED (evo-079)
**Found:** AI Visual Analysis (evo-079) — rated explore panel 3/10 despite 6+ previous fix rounds
**Problem:** Panel background (`#1a2d48` → `#0e1e34` gradient) was too similar to the dark game canvas. Cards had small thumbnails (72x56px) and dim text. On mobile, panel was `display: none !important` — visitors had NO navigation to other islands on mobile at all.
**Fix:**
- [x] Panel background dramatically brightened: `rgba(22,44,72,0.98)` solid with lighter gradient
- [x] Top border strengthened: 3px solid `rgba(100,200,255,0.9)` with pulsing glow animation (4s on load)
- [x] Inner glow shadow added for clear visual separation from game canvas
- [x] Card thumbnails enlarged: 72x56 → 80x62px desktop, border more visible
- [x] Text sizes bumped: name 13→14px, owner/stats 11→12px
- [x] Card dimensions increased: min-width 190px, max-width 250px, padding 14px 16px
- [x] **Mobile explore panel restored** — removed `display: none !important` on ≤600px
- [x] Mobile layout: horizontal scrollable cards with 60x46px thumbnails, 140px max panel height
- [x] Pulsing blue glow `@keyframes explorePulse` draws attention on first appearance

### ISSUE-066: Lobby Card Metadata Overload — ✅ FIXED (evo-079)
**Found:** AI Visual Analysis (evo-079) — rated card readability 6/10, first-time UX 5/10
**Problem:** Each card showed 4 competing stat elements (type badge, level, visits, objects count) plus 2-line bio text. Too dense for quick scanning. Objects count not meaningful to first-time users.
**Fix:**
- [x] Removed objects count from desktop stats row — cards now show Type · Level · Visits only
- [x] Bio text reduced to single-line ellipsis on desktop (was 2-line clamp)
- [x] Bio opacity reduced 0.75 → 0.6 for clearer secondary hierarchy
- [x] Island name bumped 14→15px with text-shadow for stronger visual anchor
- [x] Owner "by" prefix dimmed to opacity 0.4 (was 0.5)
- [x] New Islands cards show only Level (removed visits/objects — all 0 anyway)

### ISSUE-067: Mobile Island Bottom UI Stacking — Claw Speech Blocks Explore Panel — ✅ FIXED (evo-080)
**Found:** AI Visual Analysis (evo-080) — rated mobile explore panel 2/10, mobile visitor experience 5/10
**Problem:** On mobile (≤600px), claw speech bubble (bottom: 140px) overlapped the Explore More Islands panel (bottom: 0, max-height: 140px). Both elements competed for the bottom third of the screen. Visitors on mobile saw no usable navigation to other islands while speech was visible.
**Fix:**
- [x] Added `body.claw-speech-active` CSS class that hides explore panel (opacity: 0, pointer-events: none) while speech is visible on mobile
- [x] JS: `classList.add('claw-speech-active')` on speech show (mobile only), removed on fade/dismiss/close
- [x] Claw speech repositioned higher: bottom 140→160px on mobile for extra clearance
- [x] Auto-fade reduced to 5s on mobile (was 6s) so explore panel appears sooner
- [x] Close button (✕) handler also removes the class for instant explore panel reveal
- [x] Explore panel fades in with 0.5s transition after speech dismisses — clean sequenced flow

### ISSUE-068: Mobile Lobby Card Readability — ✅ FIXED (evo-080)
**Found:** AI Visual Analysis (evo-080) — rated mobile card readability 4/10, touch targets 5/10
**Problem:** On mobile (≤500px), card stats metadata too small and dense. Stats items were font-weight 600 at 14px. Touch targets borderline at 36px. Owner name 12px too small.
**Fix:**
- [x] Island name: 15→16px with letter-spacing: 0.3px for better legibility
- [x] Owner name: 12→13px, color brightened to #d8e8f4
- [x] Stats: font-weight 600→700, font-size 15px, gap 6→8px
- [x] Stats row background: opacity 0.05→0.08 for better visibility
- [x] Stats row min-height: 36→40px for better touch targets
- [x] Card min-height: 220px for consistent card sizing
- [x] Card info padding: 14px horizontal for breathing room

### ISSUE-069: Explore Panel Collapsed by Default — ✅ FIXED (evo-081)
**Found:** AI Visual Analysis (evo-081) — rated island bottom UI clutter 3/10 (mobile), 6/10 (desktop)
**Problem:** "Explore More Islands" panel occupied 130-160px at the bottom of the island page permanently, reducing focus on the actual island content. AI's #1 recommendation: collapse the panel by default.
**Fix:**
- [x] Explore panel defaults to collapsed state: slim ~40px header bar showing "🏝️ Explore More Islands · N online  View All → ▲"
- [x] Click/tap header bar to expand and reveal full card-based panel
- [x] Collapse chevron (▼) to re-minimize when expanded
- [x] Mobile (≤600px): even more compact collapsed bar (~36px)
- [x] `explore-collapsed` CSS class controls collapsed state with smooth transitions
- [x] Close (✕) and minimize (▼/▲) buttons both functional
- [x] "View All →" link remains clickable in collapsed state
- [x] AI re-rated: island visibility 9/10 (up from ~7/10), bottom clutter significantly reduced

### ISSUE-070: Mobile Lobby Above-Fold Compaction — ✅ FIXED (evo-081)
**Found:** AI Visual Analysis (evo-081) — rated mobile lobby above-fold density 4/10
**Problem:** On mobile (390px), hero title, onboarding steps, CTA banner, filter bar, and section titles consumed excessive vertical space, pushing island cards far below the fold.
**Fix:**
- [x] Onboarding steps hidden entirely on mobile (≤600px) — duplicated CTA messaging
- [x] CTA banner hidden on mobile, replaced with inline "🦞 Create Your Island" button in hero section
- [x] Hero padding further reduced: 8px top, 2px bottom
- [x] Section titles compacted: 11px font, tighter margins
- [x] Filter bar more compact: 34px button height, tighter padding/gaps
- [x] `.mobile-hero-cta` hidden on desktop via min-width:601px media query
- [x] AI re-rated: above-fold density 8/10 (up from 4/10!), card readability 7/10 (up from 5/10)

### ISSUE-071: Island Camera Zoom — Island Too Small in Viewport — ✅ FIXED (evo-082)
**Found:** AI Visual Analysis (evo-082) — rated island visibility 4/10 (desktop), 2/5 (mobile)
**Problem:** Despite previous zoom boosts (evo-034, evo-046, evo-069), the island still appeared too small relative to the viewport. Excessive ocean/water background visible, making buildings hard to distinguish. AI noted "island feels distant" and recommended zooming in further.
**Fix:**
- [x] Horizontal zoom multiplier: `cw * 1.1` → `cw * 1.4` (+27%)
- [x] Vertical zoom multiplier: `ch * 1.0` → `ch * 1.2` (+20%)
- [x] Mobile zoom boost: `1.3x` → `1.5x` (+15%)
- [x] Tablet zoom boost: `1.15x` → `1.3x` (+13%)
- [x] Max zoom cap: `2.5` → `3.0` for small islands
- [x] Island now fills ~85-95% of viewport on all screen sizes

### ISSUE-072: Mobile Bottom Nav Shown to Visitors — ✅ FIXED (evo-082)
**Found:** AI Visual Analysis (evo-082) — "Guestbook" visible at bottom on mobile visitor view
**Problem:** The `#mobile-nav` (View/Bag/Shop/Book/More) was always shown on mobile ≤600px, including to visitors. Visitors can't use Bag/Shop/View mode — these are owner-only actions. The nav took 52px of space and showed confusing buttons.
**Fix:**
- [x] Added `body:not(.owner-view) #mobile-nav { display: none !important }` — visitors see no bottom nav
- [x] Explore panel repositioned to `bottom: 0` for visitors (was 52px to clear nav)
- [x] Guestbook panel properly hidden via `display:none` (was `display:flex` overriding `display:none`)
- [x] Guestbook mobile bottom: 0 for visitors, 52px for owners via `body.owner-view` override
- [x] Explore header shortened on mobile: "Explore Islands" instead of "Explore More Islands"
- [x] Mobile visitor view now clean: full-screen island + slim explore bar at bottom

### ISSUE-073: Island Visitor Navigation Clarity — ✅ FIXED (evo-083)
**Found:** AI Visual Analysis (evo-083) — rated navigation clarity 6/10
**Problem:** Visitors had no clear way to navigate back to the lobby. The "←" back arrow had no label. The "🏝️ Islands" button was vague — visitors didn't know what it did. No "Home" or "Lobby" label anywhere.
**Fix:**
- [x] Back arrow restored to "← Lobby" on desktop (>600px) — clear destination label
- [x] Mobile (≤600px) keeps just "←" to save space + 🏠 emoji button
- [x] "🏝️ Islands" button renamed to "🏠 Lobby" with clearer title
- [x] Desktop: hidden redundant 🏠 Lobby button (← Lobby text is sufficient)
- [x] Mobile: 🏠 emoji-only button shown (complements arrow-only back link)
- [x] Single clear navigation path on each viewport — no redundant elements

### ISSUE-074: New Islands Missing Freshness Context — ✅ FIXED (evo-083)
**Found:** AI Visual Analysis (evo-083) — rated New Islands section 7/10
**Problem:** "NEW" pills were small and didn't communicate *how* recent an island was. No indication of creation time — "new" could mean 1 hour or 1 week old.
**Fix:**
- [x] Backend: Added `created_at` to `/api/islands` response
- [x] Frontend: "Created Xh/Xd ago" relative timestamp below stats row on New Islands cards only
- [x] Styled as 10px italic muted text (#7898b8) — clearly secondary
- [x] Active Islands and Featured sections unchanged
- [x] Uses existing `timeAgo()` helper function

### ISSUE-075: Explore Bar Collapsed State Invisible — ✅ FIXED (evo-084)
**Found:** AI Visual Analysis (evo-084) — rated explore bar 2/10 on desktop
**Problem:** Collapsed "Explore More Islands" bar blended into the dark game canvas. AI couldn't even read the text — described it as a "thin dark strip" with "no readable text." Visitors had no visible navigation to other islands.
**Fix:**
- [x] Collapsed bar background: bright blue gradient (`rgba(20,50,90,0.98)` → `rgba(30,70,120,0.98)`) that contrasts with game canvas
- [x] Top border: 2px solid `rgba(100,200,255,0.8)` — bright cyan accent
- [x] Pulsing glow animation (`collapseBarPulse`) — 3 pulses on load drawing attention
- [x] Hover state: brighter background + cyan border + stronger glow
- [x] Header text: 15px white with text-shadow for readability
- [x] Added "Click to explore ▲" hint text in collapsed header
- [x] "View All →" link styled bright #88ccff
- [x] Bar height increased 40→46px for better presence
- [x] Bar is now visually distinct from game canvas — looks clickable, not decorative

### ISSUE-076: Mobile Island Zoom Still Too Small — ✅ FIXED (evo-084)
**Found:** AI Visual Analysis (evo-084) — rated mobile island visibility 5/10
**Problem:** Despite 4 prior zoom passes (evo-034, -046, -069, -082), island still appeared too zoomed out on mobile (390px). "Interactive details/tap targets are tiny, much of the view is wasted on ocean."
**Fix:**
- [x] Base horizontal multiplier: `cw * 1.4` → `cw * 1.6` (+14%)
- [x] Base vertical multiplier: `ch * 1.2` → `ch * 1.4` (+17%)
- [x] Mobile zoom boost (≤500px): 1.5x → 1.8x (+20%)
- [x] Tablet zoom boost (≤768px): 1.3x → 1.5x (+15%)
- [x] Max zoom cap: 3.0 → 3.5 for small islands
- [x] AI re-rated mobile: 5/10 → 8/10 overall, 7/10 fill, 8/10 clarity

## 🔴 [EVAL-FOUND] External Model Findings (2026-03-23)
**Source:** Blind review by GPT-5.2 via gsk analyze. The eval model had NO knowledge of what was built or intended.

### ISSUE-077: [EVAL-FOUND] No Clear CTA on Island Page — ✅ FIXED (evo-085)
**Eval score:** Clarity 4/10
**Problem:** A first-time visitor lands on an island and sees a pretty map, but has zero indication of what they should DO.
**Fix:**
- [x] Replaced minimal "Got it" toast bar with proper visitor welcome card
- [x] Card shows island name + owner with 3 clear CTAs: "🎮 Start Exploring" (primary), "📝 Guestbook" (secondary), "🏝️ Create Your Own" (secondary)
- [x] Solid opaque background (#061030) with high-contrast border for maximum readability
- [x] Card deferred until loading screen hides (user sees it for full 12s)
- [x] Explore panel hidden while welcome card visible (no competing elements)
- [x] FARM building label: touch-aware ("Tap to Enter" on mobile, "Click to Enter" on desktop)
- [x] Claw speech simplified: removed confusing "Got it" CTA buttons
- [x] Card dismissable by clicking outside, close button, or any CTA button

### ISSUE-078: [EVAL-FOUND] Lobby Has Two Competing CTAs — ✅ FIXED (evo-085)
**Eval quote:** "Both are presented as strong CTAs near the top; unclear which is the primary path for new users. Decision paralysis."
**Problem:** New user sees both "Join/Login" and "Create Your Island" as prominent buttons. Unclear which to click.
**Fix:**
- [x] Removed "🦞 Join / Login" button from hero stats area
- [x] Replaced with subtle "Log in" text link (secondary, less prominent)
- [x] Single clear CTA path: "🦞 Create Your Island" (mobile hero button + desktop CTA banner)
- [x] Featured cards: hide visit count when < 10 visits (avoids "dead game" impression)
- [x] Hidden "Log in" text link on mobile (mobile-hero-cta is the sole CTA)

### ISSUE-079: [EVAL-FOUND] "Filter & Sort" Control Is Ambiguous — ✅ FIXED (evo-086)
**Eval quote:** "A combined control with dropdown indicator but looks like a search bar; no hint of current sort/filter state."
**Problem:** Users don't know if it's a search box, a dropdown, or what's currently selected.
**Fix:** Split into clear separate controls or show current state (e.g., "Sorted by: Popular ▾").

### ISSUE-080: [EVAL-FOUND] Featured Card "Got it" Button Purpose Unclear — ✅ FIXED (evo-085)
**Eval quote:** "'Got it' refers to... what? There's no preceding instruction or context."
**Problem:** The "Got it" button at the bottom of island view dismisses... something, but the user doesn't know what they're acknowledging.
**Fix:** Replace with actionable text like "Start Exploring" or remove if unnecessary.


### ISSUE-081: Lobby Card Visit Button + Text Size — ✅ FIXED (evo-088, evo-092)
**Found:** GPT-5.2 eval rated card readability 4/10, CTA clarity 5/10
**Problem:** "Visit" was just a hover overlay text, not a real button. Card text too small. Stats too cluttered (4 items).
**Fix (evo-088):**
- [x] Added proper "Visit Island →" button to every island card (full-width, blue border/bg, proper touch target)
- [x] Island name: 15→17px desktop, 16px mobile
- [x] Owner name: 12→13px
- [x] Stats: 13→14px desktop, 15px mobile
- [x] Removed objects count from stats (meaningless to users)
- [x] Removed old ::before hover overlay "Visit →" pseudo-element
- [x] Post-fix AI re-eval: 4/10 → 6/10 readability
**Fix (evo-092):**
- [x] Island name: 17→19px desktop, 16→17px mobile
- [x] Owner name: 13→14px desktop, 12→13px mobile
- [x] Stats: 14→15px desktop
- [x] Visit button: switched from pixel font to UI font (var(--font-ui)), 12→13px, font-weight 600
- [x] Avatar emoji: 32→36px for better visual hierarchy
- [x] Header gap: 10→12px for breathing room

### ISSUE-082: "by by [name]" Owner Name Duplication on Desktop — ✅ FIXED (evo-091)
**Found:** Visual audit during evo-091 cycle
**Problem:** Desktop lobby cards displayed "by by Eric J" instead of "by Eric J". Root cause: CSS `.owner-name::before { content: 'by ' }` added the prefix visually, AND JavaScript `renderIslandCard()` also prepended "by " to the `ownerLabel` variable.
**Fix:**
- [x] Removed "by " prefix from JS `renderIslandCard()` ownerLabel — CSS `::before` handles it
- [x] Featured cards (`.featured-owner`) correctly kept JS "by " since that class has no CSS `::before`
- [x] Mobile (≤500px) correctly hides `::before` so just shows the name
- [x] Verified desktop and mobile both display correctly

### ISSUE-083: Featured Islands Duplicated in Popular — ✅ FIXED (evo-094)
**Found:** GPT-5.2 eval rated lobby at 7/10, noted "repeated content (Featured items also in Popular) can feel redundant"
**Problem:** The 3 Featured islands also appeared in the Popular Islands grid below, causing visual duplication.
**Fix:**
- [x] Store featured `world_id`s in a Set during `buildFeaturedSection()`
- [x] Filter them out from `activeIslands` before building Popular Islands grid
- [x] Only exclude in default view — search/filter results show all matching islands
- [x] Popular now shows 16 islands instead of 19

### ISSUE-084: Mobile Island Zoom Still Too Far Out (v6 fix) — ✅ FIXED (evo-094)
**Found:** GPT-5.2 rated mobile island visibility 6/10: "substantial unused water space"
**Root cause:** Bounding box calculation included water/ocean tiles at island edges, inflating the extent beyond actual island landmass.
**Fix:**
- [x] Exclude water tiles (`tileId.startsWith('water')`) from bounding box computation
- [x] Use only land terrain tiles + placed objects for content extent
- [x] Add 1-tile margin around tight land bounds
- [x] Mobile zoom boost: 1.8x → 2.2x, tablet: 1.5x → 1.6x
- [x] Base multipliers bumped: horizontal 1.6→1.8, vertical 1.4→1.6
- [x] Max zoom cap: 3.5 → 4.0
- [x] Mobile vertical center: 0.40 → 0.45

## 🔴 [EVAL-FOUND] GPT-5.2 Blind Review (2026-03-23, Lobby 4/10)

### ISSUE-085: Lobby Excessive Repetition / Scroll Fatigue — ✅ FIXED (evo-095)
**Eval score:** 4/10 overall
**Problem:** Popular Islands + Recently Created sections show overlapping content with identical card styles. Mobile users scroll through 28+ tall cards. "Repeated sections feel like duplicates."
**Fix:**
- [x] Merged Popular + Recently Created into single "🏝️ All Islands (N)" section
- [x] New islands (< 7 days) tagged with inline ✨ NEW badge + "Created X ago" timestamp
- [x] Mobile card thumbnails reduced 180→140px, tighter padding
- [x] "Load N more islands ↓" button with loading feedback

### ISSUE-086: Search Bar Visually Weak — ✅ FIXED (evo-095)
**Eval quote:** "Search blends into the dark UI and doesn't look clearly actionable"
**Fix plan:** Increase search contrast, add icon, make sticky or more prominent

### ISSUE-087: Card Information Hierarchy Messy — ✅ FIXED (evo-096, evo-097)
**Eval quote:** "Users likely choose based on type/level/active but layout prioritizes decorative tags and inconsistent metadata"
**Fix:**
- [x] Card hierarchy standardized: Level (14px bold) > Type badge > Visits > Bio > Created (evo-096)
- [x] Bio text dimmed but readable: solid #8899aa color, no double-opacity (evo-097)
- [x] "Created X ago" timestamp: 10px/0.65 opacity, now legible (evo-097)
- [x] Visit button shortened to "Visit →" (evo-096)

### ISSUE-088: "Show More" Button Vague — ✅ FIXED (evo-095)
**Eval quote:** "'Show More (9 remaining)' is vague; unclear what happens"
**Fix:**
- [x] Changed to "Load N more islands ↓" with loading state feedback

### ISSUE-089: End-of-List Message Misleading — ✅ FIXED (evo-095)
**Eval quote:** "'You've explored all islands!' is misleading — user only scrolled"
**Fix:**
- [x] Changed to "You've reached the end of the list. Try different filters or create your own island!"

### ISSUE-090: Top Stats Bar Not Actionable — ✅ FIXED (evo-096)
**Eval quote:** "Stats consume prime space without helping the user choose or act"
**Fix:**
- [x] Type stats (farms, fisheries, mines, forests) are now clickable — calls `switchType()` to filter
- [x] Added `.stat-link` CSS class with pointer cursor, dotted underline, and hover brightening
- [x] Active type stat highlighted with bold + solid underline (`.stat-active`)
- [x] Total islands and total visits remain non-clickable (not filterable)
- [x] Online count preserved when stats re-render on type switch

## 🔴 [EVAL-FOUND] GPT Blind Review (2026-03-23, Lobby Mobile 390px, 3/10)

### ISSUE-091: [EVAL-FOUND] Search Bar Too Small on Mobile — ✅ FIXED (evo-118)
**Eval quote:** "Search blends into the dark UI and doesn't look clearly actionable"
**Problem:** Search controls are small and not prominent enough on mobile. Users can't easily find/filter islands.
**Fix plan:** Make search bar full-width, higher contrast, sticky at top. Add clear filter/sort controls.

### ISSUE-092: [EVAL-FOUND] Wall-of-Cards Fatigue / No Segmentation — ✅ FIXED (evo-119)
**Eval quote:** "Repetitive card structure with minimal whitespace; scanning becomes tiring"
**Problem:** All islands show in one undifferentiated list. No categories like "Popular", "New", "For You".
**Fix:**
- [x] Lobby segmented into 3 sections: 🆕 New Islands (≤7 days, max 6), 🔥 Popular (top 8 by score), 🏝️ All Islands (rest)
- [x] Each section has its own `.section-title.segment-header` with subtle visual divider
- [x] Segmentation only active in default view — search/filter shows flat list
- [x] `animIndex` continuous across sections for smooth staggered animation
- [x] i18n support for all 8 languages in `i18n.js`

### ISSUE-093: [EVAL-FOUND] No Sort Feedback or Visible Sort State — ✅ FIXED (evo-120)
**Eval quote:** "Users don't know if they're seeing best, newest, or random"
**Problem:** Current sort/filter controls exist but aren't visible enough on mobile. Users don't know what ordering they're seeing.
**Fix:**
- [x] Mobile: "Showing: 🔥 Popular" sort indicator strip below filter toggle — always visible without expanding
- [x] Indicator updates dynamically with sort mode, type filter, and search terms
- [x] Non-default filter state: toggle highlighted with blue bg/border/glow (`.has-filters` enhanced)
- [x] Desktop: `.sort-btn.active` gets underline indicator (2px cyan bar via `::after`)
- [x] i18n: "filter.showing" key added for all 8 languages

### ISSUE-094: Mobile Lobby Card Truncation / Show More — ✅ FIXED (evo-121)
**Found:** GPT Blind Review (Lobby Mobile 390px, 3/10) — "wall of cards fatigue"
**Problem:** All 33+ cards visible on mobile at once, creating endless scroll. Page was extremely long with repetitive card layout.
**Fix:**
- [x] Section card limits on mobile (≤500px): New Islands max 4, Popular max 4, All Islands max 6
- [x] "Show X more ▾" / "Show less ▴" buttons per section
- [x] Compact mobile cards: 140px thumbnails (was 180px), hidden bio, tighter padding
- [x] Visit button smaller on mobile: 10px padding, 13px font
- [x] Card gap reduced 20px → 14px on mobile
- [x] Dynamically adapts on resize, disabled during search/filter

### ISSUE-095: Mobile Card Redundant Visit Buttons + Stats Overload — ✅ FIXED (evo-136)
**Found:** GPT-5.2 eval rated card readability 5/10, CTA clarity 6/10, above-fold 6/10
**Problem:** Every mobile card had a "Visit →" button taking ~30px despite entire card being tappable. Stats showed Level + Type + Visits (too many). Onboarding strip wasted above-fold space.
**Fix:**
- [x] Hidden `.card-visit-btn` on mobile (≤500px) — entire card is tappable
- [x] Hidden `.stat-visits` on mobile — cards show only Level + Type badge
- [x] Hidden `.onboarding-strip` on mobile (≤600px) — saves ~60px above-fold
- [x] Hidden `.card-tap-arrow` on mobile — redundant
- [x] GPT-5.2 top 3 recommendations all addressed
