#!/bin/bash
# Clawverse Self-Evolution Cycle
# Called by cron every 2 hours
# This script sends a heartbeat-style message to OpenClaw to trigger an evolution cycle

# Notify OpenClaw to run an evolution cycle
openclaw system event --text "CLAWVERSE_EVOLUTION_CYCLE: Time for the next evolution sprint. Read /opt/clawverse/EVOLUTION.md for the process. Read /opt/clawverse/ISSUES.md for the backlog. Read /opt/clawverse/evolution_log.jsonl for history. Execute the cycle: Screenshot → Analyze → Plan → Code (sub-agents) → Test → Reflect → Report to Eric's Slack (U08NW697WM7). Pick the highest priority unresolved issue and fix it." --mode now
