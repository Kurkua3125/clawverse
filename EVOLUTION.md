# Clawverse Self-Evolution System v2

**Created**: 2026-03-22
**Updated**: 2026-03-22 02:00 UTC
**Purpose**: 24/7 autonomous development with full VM capability exploitation

---

## VM Capability Inventory

| Resource | Spec | How We Use It |
|----------|------|---------------|
| **CPU** | 2 cores Xeon E5-2673 v4 | Parallel sub-agents (2 concurrent) |
| **RAM** | 7.7 GB (5.9 GB available) | Browser + backend + 2 coding agents |
| **Disk** | 48 GB free | Screenshots, logs, test artifacts |
| **Browser** | Chromium + Playwright + noVNC | Visual regression testing, screenshot diffing |
| **Playwright** | v1.58.2 | Automated E2E testing, multi-viewport |
| **ffmpeg** | v6.1.1 | Screen recording of test runs |
| **ImageMagick** | v6.9.12 | Screenshot comparison / diff |
| **Coding Agents** | Claude Code, Codex, OpenCode | Parallel task execution |
| **PM2** | Process manager | Persistent backend process |
| **tmux** | Terminal multiplexer | Session persistence |
| **Caddy** | Reverse proxy + auto-HTTPS | Zero-downtime deploys |
| **SQLite** | v3.45.1 | Database |
| **Python + Node** | Python 3 + Node 22 | Full stack |
| **Network** | Ports 80/443/8443/3000/8000-8999 | Multiple service endpoints |
| **gsk CLI** | Genspark AI services | Image gen, web search, AI analysis |

---

## Architecture v2: Maximizing VM Advantages

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CRON SUPERVISOR (every 20 min)                     │
│  Reads evolution_state.json → Decides action → Spawns cycle          │
│  Reports to Eric's Slack every 20 min                                │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│              EVOLUTION CYCLE (per sprint)                             │
│                                                                       │
│  Phase 0: READ DESIGN INTELLIGENCE (MANDATORY FIRST STEP)            │
│  ├─ Read DESIGN_INTELLIGENCE.md — absorb accumulated wisdom          │
│  ├─ Understand: visitor vs owner, mobile-first laws, golden path     │
│  └─ This frames everything else. Skip this = repeat past mistakes.   │
│                                                                       │
│  Phase 1: EMPATHY WALK (replaces old shallow "observe")              │
│  ├─ Clear localStorage, resize to 390x844                            │
│  ├─ Walk the Golden Path as a BRAND NEW USER:                        │
│  │   1. Open lobby → first impression (3-second rule)                │
│  │   2. Click an island → what do I see? (70% map rule)             │
│  │   3. Try each button → does it make sense? Anything broken?       │
│  │   4. Try to leave a guestbook message → is the flow smooth?       │
│  │   5. Go back to lobby → try "Create Your Island"                  │
│  ├─ Screenshot each step                                             │
│  ├─ At each step ask: "Would a 12-year-old understand this?"         │
│  ├─ Also: API health check, JS console errors, Playwright tests     │
│  └─ Compare screenshots with previous cycle                          │
│                                                                       │
│  Phase 2: REFLECT DEEPLY (not just list bugs)                        │
│  ├─ What's the #1 friction point in the Golden Path right now?       │
│  ├─ What would Animal Crossing do differently?                       │
│  ├─ Is any element violating Mobile-First Laws?                      │
│  ├─ Are visitors seeing owner-only UI? (check every element)         │
│  ├─ Read ISSUES.md backlog                                           │
│  └─ Prioritize by USER IMPACT, not code complexity                   │
│                                                                       │
│  Phase 3: PLAN (with design reasoning)                                │
│  ├─ Select 1-3 tasks — each must explain WHY it matters to users    │
│  ├─ Write task specs for sub-agents                                  │
│  └─ Determine if tasks can run in parallel                           │
│                                                                       │
│  Phase 4: CODE (VM advantage: parallel sub-agents)                   │
│  ├─ Spawn up to 2 sub-agents simultaneously                         │
│  ├─ Each agent gets isolated task + file scope                       │
│  ├─ Monitor via sessions_list / process log                          │
│  └─ Timeout: 10 min per agent                                        │
│                                                                       │
│  Phase 5: DEPLOY                                                      │
│  ├─ Restart backend (PM2 for zero-downtime)                          │
│  ├─ Bump version counter → trigger frontend refresh banner           │
│  └─ Wait 3s for startup                                              │
│                                                                       │
│  Phase 6: TEST (VM advantage: Playwright E2E)                        │
│  ├─ Run Playwright test suite                                        │
│  ├─ Screenshot after deploy                                          │
│  ├─ API endpoint verification                                        │
│  ├─ Visual diff with pre-deploy screenshots                          │
│  ├─ If regression detected → auto-revert (git checkout)              │
│  └─ Record test artifacts in /opt/clawverse/test-artifacts/ │
│                                                                       │
│  Phase 7: REFLECT (use DESIGN_INTELLIGENCE.md template)              │
│  ├─ Answer ALL 5 reflection questions from DESIGN_INTELLIGENCE.md    │
│  ├─ 1. What did I learn about USERS this cycle?                      │
│  ├─ 2. What's the single biggest friction point remaining?           │
│  ├─ 3. What would Animal Crossing do differently?                    │
│  ├─ 4. What am I proud of?                                          │
│  ├─ 5. What should I have caught earlier?                            │
│  ├─ Update DESIGN_INTELLIGENCE.md with new learnings                 │
│  ├─ Update ISSUES.md (close resolved, add discovered)                │
│  └─ Append to evolution_log.jsonl                                    │
│                                                                       │
│  Phase 7b: EXTERNAL EVAL (every 5 cycles)                            │
│  ├─ Run: bash scripts/run_eval.sh                                    │
│  ├─ This uses gsk analyze (GPT-5.2) — a DIFFERENT model              │
│  ├─ Compare eval findings to what evolution found                    │
│  ├─ Any issue eval found but evolution missed → [EVAL-FOUND] tag     │
│  ├─ Add new EVAL-FOUND issues to ISSUES.md as HIGH PRIORITY          │
│  └─ If clarity/usability scores drop → HALT and alert Eric           │
│                                                                       │
│  Phase 8: REPORT                                                      │
│  ├─ Slack message to Eric with before/after screenshots              │
│  ├─ Include: tasks done, visual diffs, test results, reflection      │
│  ├─ If eval was run: include eval scores + new issues found          │
│  └─ Update evolution_state.json                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Automated Test Suite

File: `/opt/clawverse/tests/e2e_test.py`

Uses Playwright Python to test:
1. Lobby page loads, island cards render
2. Login flow (email input visible)
3. Island page loads for 3 different world IDs
4. Farm mode accessible
5. API endpoints return 200 + valid JSON
6. Mobile viewport (390x844) renders correctly
7. No JS console errors
8. Page load time < 3 seconds

File: `/opt/clawverse/tests/api_test.py`

Tests all API endpoints:
- GET /api/status, /api/world, /api/catalog, /api/farm, /api/turnips
- GET /api/islands, /api/progress, /api/weather
- POST /api/pageview
- GET /api/auth/me

---

## Screenshot Diffing

```bash
# Take before/after screenshots
# Compare with ImageMagick
compare -metric RMSE before.png after.png diff.png 2>&1
# If diff > threshold → flag as visual regression
```

Store in: `/opt/clawverse/test-artifacts/evo-XXX/`

---

## PM2 Zero-Downtime Deploy

```bash
# Use PM2 for backend management
pm2 start /opt/clawverse/backend/app.py --name clawverse --interpreter python3
pm2 restart clawverse
pm2 save
```

---

## Parallel Sub-Agent Strategy

With 2 CPU cores and 5.9 GB available RAM:
- Max 2 concurrent coding sub-agents
- Each sub-agent: ~200-400 MB
- Backend: ~60 MB
- Browser: ~500 MB (when running for tests)

Task isolation rules:
- **Never** let two agents edit the same file
- Split: one agent on backend (app.py/db.py), one on frontend (index.html/lobby.html)
- Or: one agent on feature code, one on test code

---

## Sprint Numbering

Format: `evo-NNN`
- evo-001 through evo-999
- Sprint counter in evolution_state.json
- Each sprint logged in evolution_log.jsonl

---

## Cron Schedule

| Job | Interval | Purpose |
|-----|----------|---------|
| Evolution Supervisor | 20 min | Trigger cycle + report to Slack |
| Watchdog | 10 min | Backend health check + auto-restart |
| Version bump check | On deploy | Trigger frontend refresh |

---

## Files

| File | Purpose |
|------|---------|
| `EVOLUTION.md` | This spec |
| `ISSUES.md` | Issue backlog (priority ordered) |
| `evolution_state.json` | Current cycle state |
| `evolution_log.jsonl` | Sprint history (append-only) |
| `tests/e2e_test.py` | Playwright E2E tests |
| `tests/api_test.py` | API integration tests |
| `test-artifacts/` | Screenshots, diffs, logs per sprint |

---

## Newbie UX Walkthrough (MANDATORY every cycle)

**Source:** Eric's direct instruction (2026-03-22) — every cycle must include a systematic visual test from a first-time user's perspective.

### Method
Pretend you have **never seen Clawverse before**. Walk through every screen, every button, every panel. Ask yourself at each step:
1. **Do I know what this is?** — Is the purpose immediately clear?
2. **Do I know what to do?** — Is there an obvious next action?
3. **Can I see everything?** — Is anything clipped, overlapping, or hidden?
4. **Is it too much?** — Am I overwhelmed by information/options?
5. **Does it work?** — Does tapping/clicking do what I expected?

### Screens to test (both desktop 1280px AND mobile 390px):

**Lobby:**
- [ ] First impression — what do I see? Is it inviting?
- [ ] Can I understand what Clawverse is within 3 seconds?
- [ ] Island cards — readable? Tappable? Thumbnail clear?
- [ ] Search/filter — discoverable? Working?
- [ ] "Create Your Island" — visible? Compelling?
- [ ] Leaderboard — makes sense to a newcomer?
- [ ] Activity feed — useful or noise?
- [ ] Scroll to bottom — everything renders?

**Island page (as visitor, NOT logged in):**
- [ ] First load — what do I see? Map should dominate.
- [ ] Welcome popup — helpful? Not blocking?
- [ ] Top bar — too many buttons? Labels clear?
- [ ] Bottom nav (mobile) — all items accessible?
- [ ] Each bottom nav item: View, Bag, Shop, Book, More — open and fully visible?
- [ ] Lobster chat — charming or annoying? Overlapping anything?
- [ ] "Explore more islands" panel — useful? Not blocking the map?
- [ ] Minimap — visible? Useful?
- [ ] Guestbook — can I leave a message? Does the form work?

**Island page (logged in, own island):**
- [ ] Edit mode — palette tiles all visible? Labels readable?
- [ ] Farm mode — tools accessible? Crop info clear?
- [ ] Build/Market/Prices tabs — all content fully visible?
- [ ] Bag — shows inventory correctly?
- [ ] Settings — accessible? Modal renders?

**Cross-cutting:**
- [ ] Night mode — everything still readable?
- [ ] Transitions — panels open/close smoothly?
- [ ] Error states — what happens with no network? Empty states?
- [ ] Font sizes — nothing smaller than 10px on mobile
- [ ] Touch targets — nothing smaller than 44px on mobile
- [ ] Z-index — no overlapping panels fighting for attention

### Output
After the walkthrough, create a **prioritized list of issues** found. Add them to ISSUES.md. Fix the top 1-3 in this cycle.

---

## Quality Gates (mandatory before sprint completion)

- [ ] All API endpoints return 200
- [ ] Playwright E2E tests pass
- [ ] No visual regression (screenshot diff < threshold)
- [ ] No JS console errors
- [ ] Mobile viewport renders correctly
- [ ] **Newbie UX walkthrough completed** (see above)
- [ ] Git committed
- [ ] evolution_log.jsonl updated
- [ ] Slack report sent
