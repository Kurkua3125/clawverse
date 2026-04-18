# Clawverse External Evaluation System

**Created:** 2026-03-23
**Problem:** Self-evaluation is blind. The AI tester gives itself ever-higher scores while cycling on the same issues (e.g., 7 zoom adjustments in 90 sprints). Real evaluation needs external judges, baselines, and systematic experiments.

---

## Architecture: Cross-Model Evaluation

```
┌────────────────────────────────────────────────────┐
│                  EVAL ORCHESTRATOR                   │
│  Runs after every N evolution cycles (e.g., every 5) │
│  Or on-demand via heartbeat/manual trigger            │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌────────────────────────────────────────────────────┐
│           SCREENSHOT CAPTURE (automated)             │
│  Captures standardized screenshots:                   │
│  1. Lobby desktop (1280x800)                         │
│  2. Lobby mobile (390x844)                           │
│  3. Island "test" desktop — fresh visitor             │
│  4. Island "test" mobile — fresh visitor              │
│  5. Island "test" mobile — Shop open                 │
│  6. Island "test" mobile — Guestbook open            │
│  7. Island "test" mobile — More menu open            │
│  All with localStorage cleared (true first visit)     │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌────────────────────────────────────────────────────┐
│         EXTERNAL MODEL EVAL (cross-model)            │
│                                                       │
│  Send screenshots to a DIFFERENT model (not the one  │
│  that built it) with standardized eval prompts:       │
│                                                       │
│  Model options:                                       │
│  - gsk analyze (uses Genspark's vision model)         │
│  - Different Claude model via sessions_spawn           │
│  - GPT-4o via API if available                        │
│                                                       │
│  The eval model has NO knowledge of what was changed  │
│  or what the builder intended. Pure blind review.      │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌────────────────────────────────────────────────────┐
│              EVAL PROMPTS (standardized)              │
│                                                       │
│  For each screenshot, ask the eval model:             │
│                                                       │
│  PROMPT 1 — First Impression (3 seconds)             │
│  "You are seeing this website for the first time.     │
│   In 3 seconds, what do you think this site is?       │
│   What would you do first? Score clarity 1-10."       │
│                                                       │
│  PROMPT 2 — Usability Audit                          │
│  "List every UX problem you can find. For each:       │
│   - What's wrong                                      │
│   - Why it matters to the user                        │
│   - Severity (critical/major/minor/cosmetic)          │
│   Be harsh. Find at least 5 issues."                  │
│                                                       │
│  PROMPT 3 — Comparison (SxS)                         │
│  "Here is version A (before) and version B (after).   │
│   Which is better? List specific improvements AND     │
│   any regressions. Did anything get worse?"            │
│                                                       │
│  PROMPT 4 — Competitor Benchmark                     │
│  "Compare this to Club Penguin / Habbo Hotel /        │
│   Animal Crossing Pocket Camp mobile UI.              │
│   What are they doing better? Score 1-10 vs each."    │
│                                                       │
│  PROMPT 5 — User Journey Friction                    │
│  "A 14-year-old got a link to this site from a        │
│   friend on Discord. Walk through what they'd do.     │
│   Where would they get confused? Where would they     │
│   give up? Where would they be delighted?"            │
│                                                       │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌────────────────────────────────────────────────────┐
│             EVAL OUTPUT & TRACKING                    │
│                                                       │
│  Store results in /eval-results/eval-YYYY-MM-DD-HH/  │
│  - screenshots/                                       │
│  - eval_raw.json (full model responses)               │
│  - scores.json (extracted numeric scores)             │
│  - issues_found.json (new issues from eval)           │
│  - regression_check.json (did anything get worse?)    │
│                                                       │
│  Track scores over time → detect plateaus/regressions │
│  If scores plateau for 3+ evals → flag for human      │
│  If regression detected → halt evolution, alert Eric   │
└────────────────────────────────────────────────────┘
```

---

## Baseline Comparison: "Naive Agent" Test

Every 10 cycles, also run a **naive agent test**:
1. Spawn a fresh sub-agent with NO context about Clawverse
2. Give it only the screenshots and ask: "List all UX problems you see"
3. Compare its findings to what the evolution system found in the last 10 cycles
4. If the naive agent finds issues the evolution system missed → those are blind spots

This is the "小白龙虾 agent" comparison Eric described.

---

## Parallel Universe Experiments

When making significant design decisions, instead of trusting one "engineering intuition":

1. **Branch K variants** (e.g., 3 different mobile nav designs)
2. **Screenshot each variant** on mobile
3. **Send all K to the eval model** as blind SxS comparison
4. **Pick the winner based on eval**, not on builder preference

Implementation: use git branches or runtime CSS overrides to create variants without full rewrites.

---

## Eval Script

Location: `/opt/clawverse/scripts/run_eval.py`

```
Usage: python3 scripts/run_eval.py [--compare-with <prev-eval-dir>]
  
Steps:
1. Start browser, clear localStorage
2. Capture 7 standardized screenshots
3. Run each screenshot through 5 eval prompts via gsk analyze
4. Parse scores and issues
5. Save to eval-results/
6. If --compare-with: run SxS comparison
7. Print summary + alert on regression
```

---

## Integration with Evolution Cycles

- Every 5 cycles: auto-run eval
- Eval results feed into next cycle's Phase 2 (REFLECT)
- If eval finds critical issues the builder missed → add to ISSUES.md with [EVAL-FOUND] tag
- Track "eval-found vs builder-found" ratio over time → measures builder blindness

---

## Success Metrics

The eval system itself is successful if:
1. It catches issues the evolution system missed (>0 new issues per eval)
2. Scores trend upward over time (not plateauing)
3. Naive agent doesn't find significantly more issues than evolution system
4. No undetected regressions between evals
