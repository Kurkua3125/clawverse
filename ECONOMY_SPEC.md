# Clawverse Economy System — Implementation Spec

## Overview
Add a full economy system to the existing Clawverse isometric island game. This is Phase 1-3 of a planned feature set.

## Current Architecture
- **Backend**: Flask on port 19003, file: `/opt/clawverse/backend/app.py` (~3100 lines)
- **Database**: SQLite via `/opt/clawverse/backend/db.py` (~1170 lines)
- **Frontend**: Single-file Canvas2D engine: `/opt/clawverse/frontend/index.html` (~6000 lines)
- **Catalog**: `/opt/clawverse/catalog/catalog.json`
- **Existing features**: Farm system (crops table), coin wallet, turnip market, stealing, attacks/raids/shields tables, animals, XP/level system

## PHASE 1: Island Types + Multi-Resource Gathering + Inventory

### 1.1 Island Type Assignment
- Add `island_type` column to `worlds` table (TEXT, default 'farm')
- Types: `farm`, `fish`, `mine`, `forest`
- On new world creation, randomly assign one of the 4 types
- Existing worlds default to 'farm'
- Add API: `GET /api/island/type` → returns `{type, primary_resources, secondary_resources, weak_resources}`

### 1.2 Resource Yield Table

| Island Type | Primary (5x yield) | Secondary (1x yield) | Weak (0.2x yield) |
|-------------|--------------------|-----------------------|---------------------|
| farm | cabbage, carrot, pumpkin, turnip | wood, fruit | fish, iron_ore |
| fish | fish, shrimp, pearl | iron_ore, stone | wood, cabbage |
| mine | iron_ore, gem, stone | fish, shrimp | wood, cabbage |
| forest | wood, fruit, mushroom | cabbage | fish, iron_ore |

### 1.3 Inventory System
- New DB table `inventory`: (world_id TEXT, resource TEXT, amount INTEGER, PRIMARY KEY(world_id, resource))
- API: `GET /api/inventory` → returns all resources for current world
- API: `POST /api/inventory/add` → add resources (internal use)
- Resources stored as simple name strings: wood, iron_ore, gem, stone, fish, shrimp, pearl, fruit, mushroom, cabbage, carrot, pumpkin

### 1.4 Multi-Type Gathering Zones
Reuse the existing farm system logic but with different skins per island type. Each island gets:
- **Primary zone**: 4×4 grid (16 plots) — high yield
- **Secondary zone**: 2×2 grid (4 plots) — normal yield  
- **Weak zone**: 1×2 grid (2 plots) — very low yield

Gathering mechanics (same as existing farm):
- Click plot → place seed/net/pickaxe/sapling
- Wait for timer countdown
- Click to harvest → resources go to inventory
- Auto-accumulate: mature resources auto-add to inventory, max 8 hours buffer, then stop producing

Visual skins per type:
- 🌾 Farm: brown soil tiles, crop emojis (existing)
- 🌊 Fish: blue water tiles, 🪤→🐟→🐟🦐 emojis
- ⛏️ Mine: gray rock tiles, ⛏️→🪨→💎⛏️ emojis  
- 🌲 Forest: dark green tiles, 🌱→🌲→🪵🍎 emojis

Growth stages (3 stages each, like existing crops):
- Stage 1: Planted (seed/net/pickaxe/sapling emoji)
- Stage 2: Growing (intermediate emoji)
- Stage 3: Ready to harvest (final product emoji)

Growth times should vary by resource type (1-5 minutes, similar to existing crops).

### 1.5 Existing Farm Integration
The existing farm system for farm-type islands becomes the "primary zone". Other island types use the same code paths but with different resource outputs. The existing crop types (cabbage 2min, carrot 3min, pumpkin 5min) stay for farm islands.

### 1.6 Fix Building Prices
In `TILE_COSTS` in app.py, add prices for objects that currently default to 5:
```python
'chest': 20, 'table_wood': 12, 'gate': 15, 'flower_gate': 18,
'fountain': 35, 'statue': 30, 'swing': 15, 'treasure_map': 25,
'dock_plank': 8, 'turnip': 5, 'garden_large': 40,
```
For AI-generated objects: change cost from 0 to 20 (remove the ai_generated free override).

## PHASE 2: Crafting + Trading Market

### 2.1 Crafting System
New DB table `crafting_queue`: (id INTEGER PRIMARY KEY AUTOINCREMENT, world_id TEXT, recipe_id TEXT, start_time TEXT, done_time TEXT, collected INTEGER DEFAULT 0)

Static recipes defined in Python code:
```python
RECIPES = {
    'furniture': {'name': 'Furniture 🪑', 'inputs': {'wood': 3}, 'output': 'furniture', 'time': 10},
    'tool': {'name': 'Tool 🔧', 'inputs': {'iron_ore': 2, 'wood': 1}, 'output': 'tool', 'time': 15},
    'bento': {'name': 'Bento 🍱', 'inputs': {'fish': 2, 'fruit': 1}, 'output': 'bento', 'time': 10},
    'jewelry': {'name': 'Jewelry 👑', 'inputs': {'gem': 1, 'iron_ore': 3}, 'output': 'jewelry', 'time': 30},
    'premium_building': {'name': 'Premium Building 🏠', 'inputs': {'wood': 5, 'iron_ore': 3}, 'output': 'premium_building', 'time': 30},
    # Weapons (Lv3)
    'axe': {'name': 'Axe 🪓', 'inputs': {'wood': 3, 'iron_ore': 1}, 'output': 'axe', 'time': 15, 'min_level': 3},
    'warhammer': {'name': 'War Hammer ⛏️', 'inputs': {'iron_ore': 3, 'stone': 2}, 'output': 'warhammer', 'time': 20, 'min_level': 3},
    'bomb': {'name': 'Bomb 💣', 'inputs': {'iron_ore': 2, 'gem': 1, 'mushroom': 2}, 'output': 'bomb', 'time': 25, 'min_level': 3},
    'torch': {'name': 'Torch 🔥', 'inputs': {'wood': 1, 'fruit': 1}, 'output': 'torch', 'time': 10, 'min_level': 3},
    # Defense (Lv3)
    'stone_wall_defense': {'name': 'Stone Wall 🧱', 'inputs': {'stone': 5}, 'output': 'stone_wall_defense', 'time': 20, 'min_level': 3},
    'watchtower': {'name': 'Watchtower 🗼', 'inputs': {'wood': 5, 'iron_ore': 3}, 'output': 'watchtower', 'time': 25, 'min_level': 3},
    'guard_dog': {'name': 'Guard Dog 🐕', 'inputs': {'fish': 10, 'cabbage': 5}, 'output': 'guard_dog', 'time': 30, 'min_level': 3},
}
```

APIs:
- `GET /api/recipes` → list all recipes (filtered by player level)
- `POST /api/craft` → start crafting (check inventory, deduct resources, add to queue)
- `GET /api/craft/status` → current crafting queue
- `POST /api/craft/collect` → collect finished item

### 2.2 Trading Market
New DB table `market_orders`: (id INTEGER PRIMARY KEY AUTOINCREMENT, seller_id TEXT, seller_name TEXT, resource TEXT, amount INTEGER, price_per_unit INTEGER, created_at TEXT, status TEXT DEFAULT 'active')

APIs:
- `GET /api/market` → list all active orders (with optional resource filter)
- `POST /api/market/sell` → create sell order (deduct from inventory)
- `POST /api/market/buy` → buy from order (deduct coins, add to buyer inventory, pay seller minus 5% tax)
- `POST /api/market/cancel` → cancel own order (return resources to inventory)
- Use database transactions for buy operations to prevent race conditions

### 2.3 Price System
New DB table `price_cycles`: (resource TEXT PRIMARY KEY, base_price INTEGER, week_seed INTEGER, pattern TEXT)

Base prices:
```python
BASE_PRICES = {
    'cabbage': 8, 'carrot': 12, 'pumpkin': 20, 'turnip': 15,
    'fish': 10, 'shrimp': 15, 'pearl': 50,
    'iron_ore': 12, 'gem': 60, 'stone': 8,
    'wood': 10, 'fruit': 8, 'mushroom': 12,
    'furniture': 40, 'tool': 35, 'bento': 30, 'jewelry': 100, 'premium_building': 80,
}
```

Daily price = base_price × daily_coefficient (0.7 to 1.5 for normal resources, 0.5 to 5.0 for turnips)
Weekly pattern types: increasing, decreasing, spike (drops then spikes), random
Use deterministic MD5-based calculation (like existing turnip system)

API: `GET /api/prices` → today's prices for all resources + 7-day history

## PHASE 3: Combat System

### 3.1 Weapon Usage
- `POST /api/attack/building` → use weapon to destroy a building on another player's island
  - Params: target_world, weapon_type, target_col, target_row
  - Deducts weapon from attacker's inventory
  - Removes building from target world
  - Records in existing `attacks` table
  - axe: destroy 1 wooden building
  - warhammer: destroy 1 stone building  
  - bomb: destroy all buildings in 3×3 area
  - torch: destroy crops/gathering plots in target
- 24-hour cooldown per target island
- 1-hour newbie protection (check world created_at)

### 3.2 Defense Buildings
- stone_wall_defense: absorbs 1 attack, then consumed
- watchtower: notifies owner + reveals attacker identity
- guard_dog: auto-counterattack, attacker loses random resource
- moat (護城河): costs 500 coins (not crafted), neutralizes bombs

API: 
- `GET /api/defense` → list active defenses
- `POST /api/defense/place` → place a defense (from inventory)
- `POST /api/defense/moat` → buy moat for 500 coins

### 3.3 Attack Cooldown
- `GET /api/attack/cooldown` → check cooldown status for target islands

## FRONTEND UI REQUIREMENTS

### Inventory Panel
- Grid layout showing all resources with emoji + count
- Opens from bottom toolbar button (📦)
- Shows crafted items and weapons too

### Gathering Zones
- Render differently per island type (different colored tiles)
- Farm: brown soil, Fish: blue water, Mine: gray rock, Forest: dark green
- Same interaction as existing farm: click to plant, click to harvest
- Show growth stage emojis
- Primary zone label, Secondary zone label, Weak zone label with yield multiplier shown

### Crafting Panel
- List of available recipes (grayed out if missing resources or level too low)
- Show required materials with green (have) / red (missing) indicators
- Click to start crafting, show progress countdown
- Flash/notify when done

### Market Panel
- Tabs: Browse / My Orders
- Browse: list all sell orders, filter by resource type, buy button
- My Orders: list own sell orders, cancel button
- Create sell order: pick resource, amount, price per unit
- Show current reference price for each resource

### Price Board
- Show all resource prices today with ↑↓ indicators vs yesterday
- Mini 7-day sparkline if possible (simple ASCII or small canvas)

### Attack UI (when visiting other islands)
- ⚔️ Attack button in toolbar (only shows on other people's islands, only if Lv3+)
- Click → select weapon from inventory → click target building → confirm dialog → destroy

### Level-Gated UI
- Lv1: Show gathering zones + inventory
- Lv2: Show crafting panel + market panel + price board
- Lv3: Show weapon recipes in crafting + attack button when visiting

## IMPORTANT IMPLEMENTATION NOTES

1. **Do NOT break existing features**: Farm, turnips, coins, visits, XP, animals — all must keep working
2. **Reuse existing patterns**: Follow the same code style as existing farm/turnip/wallet code
3. **Test all existing APIs after changes**: curl all 19+ endpoints to verify
4. **Frontend is a single file**: All UI goes in index.html, follow existing panel patterns
5. **Backend restart command**: `pkill -f "clawverse-v1.*app.py" 2>/dev/null; sleep 1; cd /opt/clawverse/backend && python3 app.py > /tmp/clawverse-v1.log 2>&1 &`
6. **Gathering zones**: The existing farm zone is at cols 10-13, rows 18-21. Add secondary zone nearby (e.g., cols 14-15, rows 18-19) and weak zone (e.g., cols 14-15, rows 20). Adjust based on island type.
7. **Level check**: Use existing `user_progress` table's `level` field
8. **Owner check**: Use existing `is_owner_request()` function for write operations
9. **World ID**: Use existing `_req_world_id()` helper for multi-world support
