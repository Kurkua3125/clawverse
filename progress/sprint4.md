# Sprint 4.0 — Farm & Claw Autonomy

**Date:** 2026-03-18
**Status:** ✅ COMPLETE — All 10 tasks passed QA

---

## Tasks Completed

### F01-FONT ✅
- Added CSS `:root` variables: `--font-xs`, `--font-sm`, `--font-md`, `--font-lg`, font families
- Fixed 65 font-size values below 8px → minimum 8px
- 0 violations remaining in QA

### F06-CROP-TILES ✅
- Generated 4 terrain tiles (128×64 px) using PIL:
  - `farmland_dry.png` — dry brown furrows
  - `farmland_wet.png` — dark moist soil
  - `field_green.png` — green growing field
  - `harvest_done.png` — golden stubble
- Generated 3 object tiles (80×80 px):
  - `turnip.png` — white/purple turnip with leaves
  - `crop_growing.png` — seedling sprouting
  - `crop_ripe.png` — full grown carrot
- All registered in `catalog.json`

### F02-FARM ✅
- `db.py`: Added `crops` table, `plant_crop()`, `get_crops()`, `harvest_crop()` functions
- `app.py`: Routes `/api/farm/crops`, `/api/farm/plant`, `/api/farm/harvest/<id>`
- Frontend: `🌱 Farm` palette tab + Farm panel with Crops/Market/Feed sub-tabs
- Plant buttons for Carrot (2min), Potato (3min), Turnip (4min)
- Visual crop progress bars with stage indicators

### F03-STEAL ✅
- Visitor-only: `is_owner_request()` check blocks owner from stealing own crops
- 1 steal per IP per day (enforced via `steal_log` table)
- SSE broadcast on steal event
- Feed event logged with thief name

### F04-TURNIP ✅
- Deterministic weekly prices via `hashlib.md5("turnip-{year}-{week}-{day}")`
- Price range: 50–500 bells
- `player_turnips` table for holdings
- Frontend Market tab with:
  - Today's price display
  - 7-day mini chart (canvas, highlights today)
  - Buy 10 / Sell All buttons

### F05-CLAW-AUTO ✅
- `GET /api/claw/action` decision tree:
  - `guard` — if recent theft
  - `harvest_reminder` — if ripe crops
  - `tend` — if growing crops
  - `idle_farm` — if no crops
  - `wander` — default
- Frontend polls every 60s, shows floating speech bubble

### F07-FEED ✅
- `feed_events` table in SQLite
- Events written on: plant, harvest, steal, turnip buy/sell
- `/api/feed` endpoint
- Scrollable Feed tab in Farm panel

### F08-PERSIST ✅
- Tested: backend restart preserves all farming data in SQLite
- DB at `backend/clawverse.db`
- Verified 1 crop + 4 feed events survived restart

### F09-DAILY-MSG ✅
- `generate_daily_bulletin()` runs on backend startup
- Report includes: ripe/growing crop count, theft count, today's turnip price
- Saved to `island_story.daily_message`
- Frontend shows scrolling bulletin bar on load (10s display)
- Sign board object exists at (17,12) in world

### F10-QA ✅
- **40/40 tests PASSED** (`/tmp/qa_sprint4.py`)
- All endpoints verified with HTTP requests
- No regressions in existing functionality

---

## Architecture Changes

```
db.py:
  + crops table
  + steal_log table
  + player_turnips table
  + feed_events table
  + init_farming()
  + plant_crop(), get_crops(), harvest_crop(), steal_crop()
  + add_feed_event(), get_feed_events()
  + get/set_player_turnips()

app.py:
  + /api/farm/crops
  + /api/farm/plant (owner only)
  + /api/farm/harvest/<id> (owner only)
  + /api/farm/steal/<id> (visitor only)
  + /api/feed
  + /api/turnip/price
  + /api/turnip/buy (owner only)
  + /api/turnip/sell (owner only)
  + /api/claw/action
  + /api/bulletin

catalog.json:
  + 4 terrain tiles (farm category)
  + 3 object tiles (crop category)

frontend/index.html:
  + :root CSS variables
  + 65 font-size fixes
  + 🌱 Farm palette tab
  + Farm/Market/Feed panel
  + Turnip market chart
  + Steal button for visitors
  + Claw speech bubble
  + Daily bulletin bar
```
