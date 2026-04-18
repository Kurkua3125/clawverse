# Clawverse Architecture & Open-Source Plan

> **Status**: Draft — 2026-03-23
> **Author**: 小红虾 (AI) + Eric J
> **Goal**: Prepare Clawverse for open-source release on GitHub, with a clean dev → production deployment pipeline.

---

## 1. Project Overview

Clawverse is an isometric browser-based virtual island builder — think Animal Crossing meets Minecraft, in a browser tab. Players build islands, grow crops, trade resources, visit each other, and interact through a persistent world.

**Tech stack**: Python (Flask) backend + vanilla JS/Canvas frontend, SQLite database, Caddy reverse proxy.

**Current state**: Single monolithic deployment on a Genspark VM, with 100+ autonomous evolution sprints completed, ~250 git commits, ~17,500 lines of code (13k frontend, 4.5k backend).

---

## 2. Current Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    Internet (Users)                         │
└──────────┬─────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────┐     ┌───────────────────────────────┐
│   Caddy (port 80/443)│     │   Caddy (port 8443)           │
│  ysnlpjle.genspark.. │     │  kunjing-5537fcd6-...:8443    │
│  → 127.0.0.1:19003   │     │  → 127.0.0.1:19003           │
└──────────┬───────────┘     └───────────┬───────────────────┘
           │                              │
           ▼                              ▼
┌──────────────────────────────────────────────────────────────┐
│                Flask Backend (port 19003)                      │
│                                                                │
│  app.py (4500 lines) — Routes, game logic, SSE, AI features  │
│  db.py  (900+ lines) — SQLite persistence layer              │
│  auth.py (250 lines) — Email-based auth (code verification)  │
│  thumbnail.py        — PIL-based isometric thumbnail gen     │
│  dashboard_route.py  — Admin dashboard route                 │
│                                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │  World JSON   │  │  SQLite DB   │  │  Tile Catalog    │   │
│  │  (worlds/*.json)│ │ clawverse.db │  │  catalog/*.png   │   │
│  └──────────────┘  └──────────────┘  └──────────────────┘   │
└──────────────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│         Frontend — Single-file SPA (index.html)               │
│                                                                │
│  Canvas-based isometric renderer (13,000 lines)               │
│  + lobby.html (island directory)                              │
│  + map.html (world map)                                       │
│  + dashboard.html (analytics)                                 │
│  + analytics.html (admin)                                     │
└──────────────────────────────────────────────────────────────┘
```

### Key Data Flows

1. **World rendering**: Browser fetches `/api/world` → JSON with terrain/objects/meta → Canvas renders isometric view
2. **Tile placement**: Owner clicks grid → `POST /api/world/place` → SQLite + JSON file updated → SSE broadcasts to visitors
3. **Auth**: Email → verification code (via `gsk email`) → session cookie → user identity
4. **Economy**: Farming → harvest → inventory → crafting → market orders → coins
5. **Social**: Visit marks, guestbook entries, gifts, stealing crops (QQ Farm style)

---

## 3. What Needs to Change for Open Source

### 3.1 Code Organization (Current → Target)

**Current problems:**
- `app.py` is 4500 lines — routes, game logic, AI features, SSE, all in one file
- `index.html` is 13,000 lines — renderer, UI, game logic, all inline
- Hardcoded paths (`/opt/clawverse/...`, `/opt/clawverse/state.json`)
- Admin email configured via `ADMIN_EMAIL` env var (no hardcoded PII)
- `.gitignore` excludes `*.db` but screenshots/test-artifacts bloat the repo (~480MB in test-artifacts, ~600MB in .git)
- No dependency management (no `requirements.txt` or `package.json`)
- AI features depend on `gsk` CLI (Genspark-specific)

**Target structure:**

```
clawverse/
├── README.md                    # Project overview, screenshots, quickstart
├── LICENSE                      # MIT or Apache 2.0
├── CONTRIBUTING.md              # How to contribute
├── CHANGELOG.md                 # Release history
├── .github/
│   ├── workflows/
│   │   ├── ci.yml               # Lint + test on PR
│   │   └── deploy.yml           # Optional: auto-deploy on push to main
│   └── ISSUE_TEMPLATE/
│       ├── bug_report.md
│       └── feature_request.md
│
├── backend/
│   ├── __init__.py
│   ├── app.py                   # Flask app factory + route registration
│   ├── config.py                # Configuration (env vars, defaults)
│   ├── models/
│   │   ├── __init__.py
│   │   ├── world.py             # World CRUD
│   │   ├── user.py              # User/auth models
│   │   ├── economy.py           # Coins, inventory, market
│   │   ├── farming.py           # Crops, ranch, gathering
│   │   ├── combat.py            # Spin, raid, attack, defense
│   │   └── social.py            # Visits, gifts, guestbook
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── world.py             # /api/world/* routes
│   │   ├── auth.py              # /api/auth/* routes
│   │   ├── economy.py           # /api/economy/* routes
│   │   ├── farming.py           # /api/farm/* routes
│   │   ├── combat.py            # /api/combat/* routes
│   │   ├── social.py            # /api/social/* routes
│   │   └── ai.py                # /api/ai/* routes (optional)
│   ├── services/
│   │   ├── auth_service.py      # Email verification logic
│   │   ├── thumbnail.py         # PIL thumbnail generation
│   │   └── ai_service.py        # AI features (pluggable)
│   ├── db.py                    # Database init + migrations
│   ├── requirements.txt         # Python dependencies
│   └── wsgi.py                  # Gunicorn/prod entry point
│
├── frontend/
│   ├── index.html               # Island view (refactored, <500 lines shell)
│   ├── lobby.html               # Island directory
│   ├── map.html                 # World map
│   ├── css/
│   │   └── style.css            # Extracted styles
│   ├── js/
│   │   ├── renderer.js          # Isometric canvas renderer
│   │   ├── editor.js            # Edit mode logic
│   │   ├── farm.js              # Farm mode UI
│   │   ├── economy.js           # Economy/shop/crafting UI
│   │   ├── social.js            # Social features UI
│   │   ├── ui.js                # Common UI components
│   │   └── api.js               # API client
│   └── assets/
│       ├── sprites/             # Lobster sprites etc.
│       └── icons/
│
├── catalog/
│   ├── catalog.json             # Tile/object definitions
│   ├── terrain/                 # Terrain tiles (128×64 PNG)
│   └── objects/                 # Object sprites
│
├── data/                        # Runtime data (gitignored)
│   ├── worlds/                  # World JSON files
│   ├── clawverse.db             # SQLite database
│   └── thumb_cache/             # Generated thumbnails
│
├── scripts/
│   ├── setup.sh                 # First-time setup
│   ├── dev.sh                   # Start dev server
│   └── deploy.sh                # Production deploy script
│
├── tests/
│   ├── test_api.py              # API endpoint tests
│   ├── test_economy.py          # Economy logic tests
│   ├── test_farming.py          # Farming logic tests
│   └── conftest.py              # Pytest fixtures
│
├── docker/
│   ├── Dockerfile               # Multi-stage build
│   └── docker-compose.yml       # Full stack (app + caddy)
│
├── docs/
│   ├── api.md                   # Full API reference
│   ├── deployment.md            # Deployment guide
│   ├── architecture.md          # This document (cleaned)
│   └── screenshots/             # README screenshots
│
├── .env.example                 # Environment variable template
├── .gitignore                   # Comprehensive gitignore
├── Makefile                     # make dev, make test, make deploy
└── Caddyfile.example            # Example Caddy config
```

### 3.2 Configuration (Hardcoded → Environment Variables)

```python
# config.py
import os

class Config:
    # Server
    HOST = os.getenv('CLAWVERSE_HOST', '0.0.0.0')
    PORT = int(os.getenv('CLAWVERSE_PORT', '19003'))
    SECRET_KEY = os.getenv('CLAWVERSE_SECRET', 'change-me-in-production')
    
    # Database
    DB_PATH = os.getenv('CLAWVERSE_DB', './data/clawverse.db')
    WORLDS_DIR = os.getenv('CLAWVERSE_WORLDS', './data/worlds')
    
    # Auth
    ADMIN_EMAIL = os.getenv('CLAWVERSE_ADMIN_EMAIL', '')
    EMAIL_PROVIDER = os.getenv('CLAWVERSE_EMAIL_PROVIDER', 'smtp')  # smtp|gsk|console
    SMTP_HOST = os.getenv('SMTP_HOST', '')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    SMTP_USER = os.getenv('SMTP_USER', '')
    SMTP_PASS = os.getenv('SMTP_PASS', '')
    
    # AI Features (optional)
    AI_ENABLED = os.getenv('CLAWVERSE_AI_ENABLED', 'false').lower() == 'true'
    AI_PROVIDER = os.getenv('CLAWVERSE_AI_PROVIDER', 'gsk')  # gsk|openai|none
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    
    # Paths
    CATALOG_DIR = os.getenv('CLAWVERSE_CATALOG', './catalog')
    FRONTEND_DIR = os.getenv('CLAWVERSE_FRONTEND', './frontend')
    THUMB_CACHE_DIR = os.getenv('CLAWVERSE_THUMBS', './data/thumb_cache')
    
    # Domain
    BASE_URL = os.getenv('CLAWVERSE_BASE_URL', 'http://localhost:19003')
```

### 3.3 Critical Refactoring Tasks

| Priority | Task | Effort | Description |
|----------|------|--------|-------------|
| P0 | Remove hardcoded paths/emails | 1 day | Replace all `/home/azureuser/...` with config-relative paths |
| P0 | Create `requirements.txt` | 30 min | Pin Flask, Pillow versions |
| P0 | Create proper `.gitignore` | 30 min | Exclude data/, *.db, test-artifacts/, screenshots/, __pycache__/ |
| P0 | Clean git history of large files | 2 hours | `git filter-repo` to remove 480MB test-artifacts from history |
| P1 | Split `app.py` into blueprints | 2 days | Extract routes into `routes/` modules using Flask Blueprints |
| P1 | Extract `db.py` into models | 1 day | Split 900-line db.py into logical modules |
| P1 | Add `config.py` | 1 hour | Environment-based configuration |
| P1 | Add Docker support | 4 hours | Dockerfile + docker-compose for easy self-hosting |
| P2 | Split `index.html` into modules | 3 days | Extract CSS/JS into separate files (biggest single task) |
| P2 | Make email auth pluggable | 4 hours | SMTP option instead of gsk-only |
| P2 | Add CI/CD workflow | 2 hours | GitHub Actions for lint + test |
| P3 | Write API docs | 1 day | OpenAPI spec or Markdown |
| P3 | Add setup wizard | 4 hours | First-run config flow |

---

## 4. Deployment Architecture (Dev → Production)

### 4.1 Two-Environment Setup

```
┌────────────────────────────────┐     ┌────────────────────────────────┐
│     DEV ENVIRONMENT            │     │     PRODUCTION ENVIRONMENT      │
│  (current VM — dev.clawverse)  │     │  (stable server — clawverse)   │
│                                │     │                                 │
│  ┌──────────────────────┐     │     │  ┌──────────────────────┐      │
│  │  Git repo (main)     │──push──→  │  │  Git repo (main)     │      │
│  │  + feature branches  │     │     │  │  auto-pull on deploy  │      │
│  └──────────────────────┘     │     │  └──────────┬───────────┘      │
│                                │     │             │                   │
│  AI evolves code here          │     │  ┌──────────▼───────────┐      │
│  Test artifacts stay here      │     │  │  deploy.sh           │      │
│  Evolution sprints run here    │     │  │  - git pull           │      │
│  Screenshots/evals run here    │     │  │  - pip install        │      │
│                                │     │  │  - run migrations     │      │
│  URL: dev.clawverse.domain     │     │  │  - restart service    │      │
│                                │     │  │  - health check       │      │
└────────────────────────────────┘     │  └──────────────────────┘      │
                                       │                                 │
                                       │  URL: clawverse.domain          │
                                       │  Stable, user-facing            │
                                       └────────────────────────────────┘
```

### 4.2 Deployment Script (`scripts/deploy.sh`)

```bash
#!/bin/bash
set -euo pipefail

APP_DIR="${CLAWVERSE_DIR:-/opt/clawverse}"
BRANCH="${DEPLOY_BRANCH:-main}"
BACKUP_DIR="${APP_DIR}/backups"

echo "🦞 Clawverse Deploy — $(date)"

# 1. Backup current database
mkdir -p "$BACKUP_DIR"
if [ -f "$APP_DIR/data/clawverse.db" ]; then
    cp "$APP_DIR/data/clawverse.db" "$BACKUP_DIR/clawverse_$(date +%Y%m%d_%H%M%S).db"
    # Keep only last 10 backups
    ls -t "$BACKUP_DIR"/clawverse_*.db | tail -n +11 | xargs -r rm
fi

# 2. Pull latest code
cd "$APP_DIR"
git fetch origin
git checkout "$BRANCH"
git pull origin "$BRANCH"

# 3. Install/update dependencies
pip3 install -r backend/requirements.txt --quiet

# 4. Run database migrations (if any)
python3 -c "from backend.db import init_db; init_db()"

# 5. Restart the service
systemctl --user restart clawverse 2>/dev/null || {
    # Fallback: kill and restart manually
    pkill -f 'clawverse.*app.py' || true
    sleep 2
    cd "$APP_DIR" && python3 -m backend.app &
}

# 6. Health check
sleep 3
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:${CLAWVERSE_PORT:-19003}/api/status)
if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Deploy successful — backend healthy"
else
    echo "❌ Deploy FAILED — health check returned $HTTP_CODE"
    exit 1
fi
```

### 4.3 Systemd Service (Production)

```ini
# /etc/systemd/user/clawverse.service
[Unit]
Description=Clawverse Backend
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/clawverse
ExecStart=/usr/bin/python3 -m backend.app
Environment=CLAWVERSE_DB=/opt/clawverse/data/clawverse.db
Environment=CLAWVERSE_SECRET=<production-secret>
Environment=CLAWVERSE_BASE_URL=https://clawverse.example.com
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
```

### 4.4 Docker Deployment (Alternative)

```dockerfile
# docker/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpng-dev libjpeg-dev && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY catalog/ ./catalog/

# Create data directory
RUN mkdir -p /app/data/worlds /app/data/thumb_cache

EXPOSE 19003
CMD ["python3", "-m", "backend.app"]
```

```yaml
# docker/docker-compose.yml
version: '3.8'
services:
  clawverse:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    ports:
      - "19003:19003"
    volumes:
      - clawverse-data:/app/data
    environment:
      - CLAWVERSE_SECRET=${CLAWVERSE_SECRET:-change-me}
      - CLAWVERSE_BASE_URL=${BASE_URL:-http://localhost:19003}
    restart: unless-stopped

  caddy:
    image: caddy:2-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy-data:/data
    depends_on:
      - clawverse

volumes:
  clawverse-data:
  caddy-data:
```

---

## 5. Data Migration Plan

### What to Migrate to Production Server

| Data | Size | Method | Notes |
|------|------|--------|-------|
| Git repo (code only) | ~15MB | `git clone` | Clean clone, no test-artifacts |
| `clawverse.db` | ~1MB | `scp` | SQLite database (all world/user/economy data) |
| `worlds/*.json` | ~2MB | Via git | World state files |
| `catalog/` | ~12MB | Via git | Tile sprites (essential) |
| `frontend/` | ~800KB | Via git | HTML/JS/sprites |
| `thumb_cache/` | ~3MB | Regenerate | Can be regenerated from world data |

### What to NOT Migrate

| Data | Size | Reason |
|------|------|--------|
| `test-artifacts/` | 480MB | Dev-only screenshots for evolution system |
| `screenshots/` | 1.6MB | Dev-only |
| `eval-results/` | 2.7MB | Dev-only evaluation data |
| `.git/` (bloated) | 611MB | Rewrite history to remove large files |
| `progress/` | 108K | Agent progress logs (dev-only) |
| `evolution_log.jsonl` | Dev log | Evolution system state |
| `evolution_state.json` | Dev state | Evolution system state |
| `EVOLUTION.md`, `ISSUES.md` | Dev docs | Convert to GitHub Issues |

### Database Schema (for reference)

Tables in `clawverse.db`:
- `worlds` — Island metadata + world JSON data + owner
- `visits` — Visitor marks (emoji + name + message)
- `page_views` — Passive visit tracking
- `user_progress` — XP, level, coins, achievements
- `crops` — Active farming crops
- `animals` — Ranch animals
- `gathering_plots` — Resource gathering zones
- `inventory` — Player resource inventories
- `crafting_queue` — Active crafting jobs
- `market_orders` — Player-to-player market
- `gifts` — Visitor gifts
- `guestbook` — Visitor messages
- `daily_spins` — Daily spin results
- `shields`, `raids`, `attacks`, `destroyed_objects` — Combat system
- `action_tokens` — Attack/raid tokens
- `defense_items` — Placed defenses
- `servants` — Automation servants
- `player_turnips` — Turnip market state
- `feed_events` — Activity feed
- `users`, `sessions`, `verification_codes` — Auth system
- `user_settings` — API keys, preferences
- `islands` — Island registry
- `island_story` — Bio/daily message
- `world_snapshots` — Named snapshots
- `evolutions` — Evolution tracking

---

## 6. GitHub Issues Integration Plan

### How It Works

1. Users file issues on GitHub (bug reports, feature requests)
2. The evolution system reads open issues tagged `ready` or `approved`
3. Each evolution sprint can pick issues from GitHub backlog
4. When a fix is committed, the commit message references the issue (`fixes #123`)
5. Merged PRs auto-close the linked issue

### Workflow

```
User files issue → Maintainer triages → Labels "ready" 
  → Evolution system picks it up → Sub-agent implements
  → PR created → Review → Merge → Issue closed
```

### Labels to Set Up

| Label | Color | Description |
|-------|-------|-------------|
| `bug` | red | Something isn't working |
| `feature` | blue | New feature request |
| `enhancement` | cyan | Improve existing feature |
| `visual` | purple | UI/design issue |
| `economy` | gold | Game economy balance |
| `mobile` | green | Mobile-specific issue |
| `ready` | bright green | Triaged and ready for implementation |
| `wontfix` | gray | Not planned |
| `duplicate` | gray | Duplicate of another issue |

### Automated Issue-to-Sprint Pipeline

The existing `HEARTBEAT.md` evolution cycle can be extended:

```python
# In evolution cycle, add a step:
# 1. Fetch GitHub issues labeled "ready"
# 2. Prioritize by: severity, votes (thumbs up), age
# 3. Convert to sprint tasks
# 4. Implement, test, commit with "fixes #N"
```

This uses the existing `gh-issues` skill in OpenClaw.

---

## 7. Open Source Checklist

### Before First Public Commit

- [ ] Remove all hardcoded paths (`/home/azureuser/...`)
- [ ] Remove hardcoded admin email / user IDs
- [ ] Add `config.py` with env var support
- [ ] Create `requirements.txt` (Flask, Pillow, gunicorn)
- [ ] Create proper `.gitignore`
- [ ] Clean git history (remove 480MB test-artifacts, screenshots)
- [ ] Add `LICENSE` (recommend MIT)
- [ ] Write `README.md` with screenshots, quickstart
- [ ] Add `.env.example`
- [ ] Make email auth pluggable (SMTP fallback)
- [ ] Test fresh setup on a clean machine
- [ ] Security audit: no secrets in code

### Nice to Have for v1.0

- [ ] Docker support
- [ ] GitHub Actions CI
- [ ] API documentation
- [ ] Contributing guide
- [ ] Issue templates
- [ ] Split monolithic files (P2, can be incremental)

---

## 8. Recommended Execution Order

**Phase 1 — Clean Up (Day 1)**
1. Create `requirements.txt` and `config.py`
2. Remove hardcoded paths and emails
3. Create proper `.gitignore`
4. Add `.env.example`, `LICENSE`

**Phase 2 — Git History Clean (Day 1)**
1. Clean large files from git history
2. Create fresh repo on GitHub
3. Push clean codebase

**Phase 3 — Refactor Backend (Days 2-3)**
1. Split `app.py` into Flask Blueprints
2. Split `db.py` into model modules
3. Add `wsgi.py` entry point

**Phase 4 — Deploy Script (Day 3)**
1. Create `deploy.sh`
2. Set up systemd service on production server
3. Configure Caddy on production server
4. First deploy + health check

**Phase 5 — CI/CD + Docs (Day 4)**
1. GitHub Actions workflow
2. README with screenshots
3. API docs
4. Issue templates

**Phase 6 — Enable Issue Pipeline (Day 5)**
1. Set up GitHub issue labels
2. Configure evolution system to read GitHub issues
3. Test end-to-end: file issue → auto-implement → PR → merge

---

*This document will be updated as the refactoring progresses.*
