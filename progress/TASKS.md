# Clawverse v1 — Active Task Board

## Current Sprint Goal
Build a polished isometric world builder that feels like Minecraft/Animal Crossing in the browser.

## Pending Tasks

### FRONTEND
- [ ] FE-01: Fix object placement from Objects palette tab (click to place objects doesn't work smoothly)
- [ ] FE-02: Add animated water tiles (shimmer effect on water_deep/water_shallow)
- [ ] FE-03: Add campfire flicker animation (canvas particle effect on campfire objects)
- [ ] FE-04: Improve agent walk path — agent should follow a path along tiles, not teleport
- [ ] FE-05: Add "New World" button — clears world and starts fresh blank island
- [ ] FE-06: Show placed object count and world name in top bar

### BACKEND
- [ ] BE-01: Add /api/world/reset endpoint — generate fresh blank world
- [ ] BE-02: Add /api/world/rename — update world name
- [ ] BE-03: Add multi-world support — /api/worlds list, /api/world/<id>/load
- [ ] BE-04: Improve AI generate — add category selector, better error messages
- [ ] BE-05: Add /api/catalog/custom — list only AI-generated tiles separately

### WORLD DESIGN
- [ ] WD-01: Generate 10 new tile types using Python PIL (dock_plank, bridge_wood, fence_wood, gate, chest, barrel, table, pond, cliff_edge, waterfall)
- [ ] WD-02: Improve default island — add dock, bridge, more variety
- [ ] WD-03: Generate night variants of tiles (darker, glowing)
- [ ] WD-04: Generate seasonal tile variants (snow on grass, cherry blossoms)

### QA
- [ ] QA-01: Take screenshots in both View and Edit mode, document what works/broken
- [ ] QA-02: Test AI Create flow end-to-end
- [ ] QA-03: Test place/remove tiles in edit mode
- [ ] QA-04: Check mobile responsiveness

## Completed
### FRONTEND (completed by frontend agent + manager)
- [x] FE-01: Fix object placement z-level ✅
- [x] FE-02: Animated water shimmer (Math.sin-based shimmer lines) ✅
- [x] FE-03: Campfire particle effect (floating fire dots) ✅
- [x] FE-04: Agent walk animation (smooth lerp interpolation) ✅
- [x] FE-05: "New World" button (🌱 New in edit mode, calls /api/world/reset + rename) ✅
- [x] FE-06: HUD tile/object count display ✅

### BACKEND (completed by manager — all existing + new)
- [x] BE-01: /api/world/reset endpoint ✅ (was pre-existing)
- [x] BE-02: /api/world/rename endpoint ✅ (was pre-existing)
- [x] BE-03: Multi-world support ✅ — /api/worlds, /api/world/<id>/load, /api/world/save-as
- [x] BE-05: /api/catalog/custom ✅ — lists AI-generated tiles

### WORLD DESIGN (completed by manager)
- [x] WD-01: Generated 8 new tiles via PIL ✅ (pond, cliff_edge_n, dock_plank, fence_wood, barrel, chest, table_wood, well)
- [x] WD-02: Improved default island ✅ — added dock, fence, barrel, table, well (11 new objects)

### QA (completed by manager)
- [x] QA-02: Backend API curl tests ✅ — all endpoints tested and passing
- [x] QA-01: Tile image audit ✅ — all 35 tiles have image files

## Notes
- Backend: Flask on :19003, code at /opt/clawverse/backend/app.py
- Frontend: /opt/clawverse/frontend/index.html (single file)
- Catalog: /opt/clawverse/catalog/
- World data: /opt/clawverse/backend/worlds/default.json
- State sync: /opt/clawverse/state.json (set_state.py)
- Restart backend: pkill -f "clawverse-v1.*app.py"; cd /opt/clawverse/backend && python3 app.py &
