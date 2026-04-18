# Clawverse Design Intelligence

**Purpose:** This is not a bug list. This is accumulated design wisdom. Every cycle reads this before making decisions. Every cycle updates it with what was learned.

**Last updated:** 2026-03-22

---

## Core UX Philosophy (derived from Animal Crossing + cozy game research)

### 1. Delight By Design
Users should feel joy at every interaction. Every click, every sound, every animation should have intentional emotional weight. The "bonk" when chopping a tree in Animal Crossing turns grinding into delight. **What's our equivalent?** Every tile placement should feel satisfying. Every crop harvest should spark joy.

### 2. Learn By Exploring, Not By Reading
Animal Crossing never shows you a manual. It drops you on an island with curiosity-hooks everywhere. You learn by touching things. **Clawverse should work the same way.** A new user should discover mechanics through interaction, not through tutorial modals.

### 3. Progressive Disclosure — Drip-Feed Complexity
Start with almost nothing. As the user succeeds at simple things, reveal more. Animal Crossing starts with: pick up sticks, craft tools, build tent. Only after days do you unlock shops, museums, terraforming. **Clawverse should hide advanced features until the user is ready.**

### 4. The "NookPhone Principle" — Meet Users Where They Are
Animal Crossing made its complex menu look like an iPhone. Users already knew how to use it. **Our UI should use patterns people already know:** bottom tab bars (like mobile apps), swipe gestures, pull-to-refresh concepts.

### 5. One Thing At A Time
Never show two competing calls-to-action. Never overlay two panels. Never demand two decisions simultaneously. **The screen should always have ONE clear thing the user can do next.**

---

## Mobile-First Laws (PERMANENT — enforced every cycle)

1. **70% Rule:** The island map must occupy ≥70% of the viewport at all times
2. **3-Second Rule:** A new user must understand what to do within 3 seconds of seeing any screen
3. **Single Panel Rule:** Only ONE panel/modal/sheet open at a time. Opening a new one closes the old one.
4. **44px Touch Rule:** No touch target smaller than 44px on mobile
5. **10px Floor:** No text smaller than 10px on any screen
6. **Safe Area:** All bottom-fixed elements must respect iOS safe area (env(safe-area-inset-bottom))
7. **No Phantom Elements:** Every visible element must be relevant to the current user's role (visitor vs owner)

---

## Visitor vs Owner — What Each Should See

### Visitor (not logged in, viewing someone's island)
**Goal:** "Wow, this is cool. I want one."
**Should see:** The map (hero), island name + owner, guestbook, a clear CTA to create their own island
**Should NOT see:** Bag, Sell, Farm tools, Edit mode, Snapshot, API Settings, Export PNG, Defense, Customize, AI Layout

### Visitor (logged in, viewing someone else's island)  
**Goal:** "Let me explore, interact, maybe trade"
**Should see:** Map, guestbook, buy from market, explore/discover, share
**Should NOT see:** Edit mode, Farm panel (for this island), owner-only tools

### Owner (on their own island)
**Goal:** "Build, farm, customize, manage"
**Should see:** Everything, progressively revealed based on level/activity

---

## User Journey Map — The Golden Path

```
1. DISCOVER: User gets a link, opens Clawverse lobby
   → First impression: beautiful island thumbnails, clear "create your own" CTA
   → Emotion: curiosity, "what is this?"

2. EXPLORE: User clicks an island card
   → Sees the island map full-screen, lobster greets them
   → Can walk around (pan), see objects, read guestbook
   → Emotion: wonder, "this is charming"

3. DESIRE: User sees something they want
   → "I want my own island" — clicks Create or Log In
   → Emotion: motivation, FOMO

4. CREATE: User creates account, gets their island
   → Starts with empty island + basic tools
   → Lobster guides first steps: "Try placing a tree!"
   → Emotion: ownership, excitement

5. BUILD: User places first objects
   → Immediate visual reward
   → Discover farming, earning coins, buying more items
   → Emotion: satisfaction, "I made this"

6. SHARE: User shares their island
   → Friends visit, leave guestbook messages
   → User visits friends' islands back
   → Emotion: pride, social connection

7. RETURN: User comes back next day
   → Crops have grown, new market prices, seasonal changes
   → Emotion: "my island is alive"
```

---

## Design Patterns — What Works (learned from cycles)

### ✅ Bottom Sheet > Side Panel (on mobile)
Side panels that slide from the right cover the entire screen and feel intrusive. Bottom sheets that slide up from the nav bar keep the island partially visible and feel natural (like iOS Maps, Uber, etc.).

### ✅ Lobster As Guide, Not Broadcaster
The lobster should speak TO the user, contextually. "Welcome! Try clicking the barn!" is better than "6 crops are ready to harvest" (which means nothing to a visitor).

### ✅ Context-Aware Menus
Show only what's relevant. Visitor menus should have 5-7 items max. Owner menus can have more, but grouped into sections.

### ✅ Panel Mutual Exclusion
Opening any panel must close all others. No stacking, no leaking.

---

## Design Anti-Patterns — What to Avoid

### ❌ Feature Dump
Showing every feature at once (17-item More menu). Overwhelms users. Always ask: "Does this user need this right now?"

### ❌ Owner UI for Visitors
Showing Bag, Sell, Farm Panel to people who can't use them. Creates confusion and wasted cognitive load.

### ❌ Pixel Counting Without User Thinking
Fixing bottom:48px→52px is correct but trivial. The deeper question is: "Should this panel exist at all for this user?"

### ❌ Checklist Auditing
Running through a list of "is X visible? ✅" is shallow testing. Deep testing is: "If I were a 12-year-old who just got this link from a friend, what would I feel?"

---

## Metrics We Should Track (aspiration)

- **Time to first action:** How long from landing to first meaningful interaction?
- **Bounce rate by page:** Do visitors leave the lobby or the island page?
- **Guestbook conversion:** What % of visitors leave a guestbook message?
- **Create-to-first-object:** How long from island creation to placing first object?
- **Return rate:** Do users come back the next day?

---

## Cycle Reflection Template

Each evolution cycle must answer these questions (not just list what was done):

1. **What did I learn about users this cycle?** (Not about code — about people)
2. **What's the single biggest friction point remaining?** (Be specific, be honest)
3. **What would Animal Crossing do differently than what I built?** (Gut check)
4. **What am I proud of from this cycle?** (Celebrate what works)
5. **What should I have caught earlier?** (Build this into future checks)

---

## Evolution Intelligence Rules

### Before coding:
- Read this file
- Walk through the Golden Path on mobile (390px) as a fresh user
- Identify the #1 friction point
- Only THEN decide what to build

### While coding:
- Test every change on mobile immediately (don't batch)
- Ask "would a 12-year-old understand this?"
- If adding a new UI element, remove one first

### After coding:
- Walk the Golden Path again
- Screenshot before/after
- Write reflection using the template above
- Update this file with any new learnings

## Lesson: Mobile Card Compaction Has a Floor (evo-103/104/105)

**What happened:** Two consecutive sprints (evo-103, evo-104) tried to make mobile cards more compact by converting from vertical cards to horizontal strip rows (~70-90px). Both scored 3/10 from GPT.

**Why it failed:** Game lobby cards are NOT data table rows. They need:
- Large enough thumbnails to show the island's personality (~140px min)
- Readable island names (14px+ on mobile)
- Visual breathing room (padding, gaps) that conveys the cozy game aesthetic
- Enough info per card (name + owner + 1-2 stats) without cramming

**The floor:** On mobile, island cards should be no shorter than ~200px including thumbnail. Single-column vertical layout is fine. Horizontal compact rows work for settings menus, not for discovery.

**Rule:** When GPT rates a layout change below 5/10, REVERT before building on top of it. Don't compound bad changes.
