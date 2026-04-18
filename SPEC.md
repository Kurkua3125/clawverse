# Clawverse v1 — Build Spec

## Vision
An isometric tile-based world builder where each user creates their own "Claw world" — 
block by block, module by module. Think Minecraft meets Animal Crossing, in a browser.

## Architecture

```
Frontend (Single Page App)
├── PixiJS v8 — Isometric rendering engine
├── Grid System — 32×32 isometric tile grid with height layers (z: 0-7)
├── Editor Mode — Drag & drop tiles/objects from palette
├── View Mode — Animated world with agent, day/night, visitors
└── State Sync — Polls backend for agent state changes

Backend (Flask on :19003)
├── GET  /api/world          — Returns world JSON
├── POST /api/world/place    — Place a tile/object
├── POST /api/world/remove   — Remove a tile/object
├── GET  /api/status         — Agent state (existing)
├── GET  /api/catalog        — Available tiles & objects
├── POST /api/visit          — Visitor footprints (existing)
├── GET  /api/visits         — Recent visits (existing)
└── GET  /                   — Serve frontend
```

## Isometric Grid System

### Coordinate System
- World grid: 32 cols × 32 rows
- Each cell: {col, row, z} where z = height layer (0 = ground, max 7)
- Tile size: 128×64 pixels (isometric diamond)
- Screen projection:
  - screenX = (col - row) * (tileWidth / 2) + offsetX
  - screenY = (col + row) * (tileHeight / 2) - z * zStep + offsetY
  - zStep = 32 pixels per height level

### Rendering Order (Painter's Algorithm)
Sort by: row ASC, col ASC, z ASC
This ensures tiles further from camera are drawn first.

## World File Format (world.json)

```json
{
  "meta": {
    "name": "My Island",
    "version": 1,
    "created": "2026-03-18T06:00:00Z",
    "theme": "tropical"
  },
  "grid": {
    "cols": 32,
    "rows": 32,
    "maxZ": 8
  },
  "terrain": [
    [0, 0, 0, "water"],
    [1, 0, 0, "sand"],
    [2, 1, 0, "grass"],
    ...
  ],
  "objects": [
    {"id": "obj_001", "type": "house_cottage", "col": 10, "row": 8, "z": 1},
    {"id": "obj_002", "type": "tree_oak", "col": 12, "row": 10, "z": 1},
    ...
  ],
  "agent": {
    "col": 10,
    "row": 9,
    "z": 1,
    "state": "idle"
  }
}
```

## Tile Catalog

### Terrain Tiles (ground layer, z=0)
Each tile = 128×64 PNG, isometric diamond shape, transparent outside diamond.
Pixel art style, consistent palette.

Categories:
- water: water_deep, water_shallow, water_shore_N/S/E/W
- sand: sand_plain, sand_shells
- grass: grass_plain, grass_flowers, grass_dark
- dirt: dirt_plain, dirt_path
- stone: stone_plain, stone_mossy

### Object Tiles (placed on terrain, z≥1)
Each object = PNG with transparent background, sized to fit on 1 or more tiles.
Objects have: footprint (1×1, 2×2, etc.), height (visual), walkable (bool).

Categories:
- structures: house_cottage, house_modern, bridge_wood, dock_wood, fence_wood
- nature: tree_oak, tree_palm, tree_pine, flower_rose, flower_tulip, rock_big, rock_small, bush_green
- furniture: desk_wood, chair_simple, campfire, mailbox, sign_wood, lantern, bench
- special: memory_tree (glowing), diary_stand, portal

### Tile Sprite Requirements
- Pixel art, 16-color or 32-color palette per tile
- Consistent lighting: top-left light source
- Consistent outline: 1px dark outline
- Ground tiles: exactly 128×64, diamond-masked
- Objects: variable height, bottom-aligned to tile grid

## Editor Mode

### UI Layout
```
┌──────────────────────────────────────────────────┐
│  [View] [Edit] [Save]              🦞 Claw World │  ← Top bar
├────────┬─────────────────────────────────────────┤
│        │                                         │
│ Palette│         Isometric Grid Canvas            │
│        │         (pannable, zoomable)             │
│ [🌊]   │                                         │
│ [🌿]   │         Click to place selected tile     │
│ [🏠]   │         Right-click to remove            │
│ [🌳]   │         Mouse wheel to zoom              │
│ [🪑]   │         Middle-drag to pan               │
│        │                                         │
│ [+ AI] │                                         │
│        │                                         │
├────────┴─────────────────────────────────────────┤
│  Height: [0] [1] [2] [3]  |  Grid: ON  | Coords │  ← Status bar
└──────────────────────────────────────────────────┘
```

### Interactions
- Left click on palette tile → select it → left click on grid → place it
- Right click on grid tile → remove top tile at that position
- Scroll wheel → zoom in/out (0.5x to 2x)
- Middle mouse drag (or two-finger) → pan the view
- Height selector → determines which z-layer you're editing
- [+ AI] button → opens prompt: "Describe what you want" → generates tile

## View Mode (Read-only, visitors see this)
- Same isometric render, but no editor UI
- Agent character walks between positions based on state
- Day/night cycle (same as current v0)
- Visitor footprint buttons at bottom
- Ambient animations: water shimmer, tree sway, campfire flicker

## Agent State Mapping
Each state maps to a tile position (configurable):
- idle → near house door
- writing → near desk
- researching → near dock/beach
- executing → near campfire
- syncing → near sign/notice board
- error → near rocks

Agent walks smoothly between positions on the isometric grid.

## Phase 1 Deliverables (this session)
1. Isometric grid engine (PixiJS) with rendering + mouse interaction
2. 15-20 pre-generated pixel art tiles (terrain + objects)
3. Editor mode: palette + click-to-place + remove
4. Backend: world load/save + catalog API
5. Basic view mode with agent
6. Deployed at same URL

## File Structure
```
/opt/clawverse/
├── SPEC.md
├── backend/
│   ├── app.py              # Flask backend
│   └── worlds/             # Stored world files
│       └── default.json    # Default world
├── catalog/
│   ├── terrain/            # Ground tile PNGs
│   ├── objects/            # Object tile PNGs
│   └── catalog.json        # Tile metadata
├── engine/
│   └── (bundled in index.html for simplicity)
├── frontend/
│   └── index.html          # Single-file app
└── scripts/
    └── generate_tiles.py   # AI tile generation script
```
