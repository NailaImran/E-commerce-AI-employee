---
name: dashboard-updater
description: Updates the Obsidian Dashboard.md file in the E-commerce vault with current order metrics, revenue, alerts, and recent activity. Use after processing new orders, when asked to "update the dashboard", "refresh stats", or "show store status". Reads summary files from /Inbox/ and /Needs_Action/ to compute counts and totals, then rewrites the dashboard sections in place.
---

# Dashboard Updater

## Overview

Reads vault state (order summaries, needs-action files) and rewrites Dashboard.md with up-to-date order counts, revenue totals, active alerts, and a recent activity log.

## Workflow

1. Scan `/Inbox/` — count pending order batch files, sum order counts and revenue
2. Scan `/Needs_Action/` — count urgent files, identify alert conditions
3. Scan `/Done/` — count completed orders today and this month
4. Rewrite each section of `Dashboard.md` using the template below
5. Update the `last_updated` frontmatter timestamp

## Running the Updater

```bash
python "E:/AI_Employee_Vault/.claude/skills/dashboard-updater/scripts/update_dashboard.py" \
  --vault "E:/AI_Employee_Vault"
```

Or instruct Claude to update Dashboard.md directly by reading the vault folders and rewriting the file sections.

## Dashboard Sections to Update

Always update ALL of these sections, never skip one:

### 1. Store Status
```markdown
## Store Status
- **Platform**: Shopify
- **Agent Tier**: Bronze
- **Last Sync**: 2026-02-21 10:30
```

### 2. Order Summary Table
Recount by scanning folder contents:
```markdown
## Order Summary
| Metric | Count |
|--------|-------|
| New Orders (Inbox) | <count from /Inbox/> |
| Needs Action | <count from /Needs_Action/> |
| Completed Today | <count from /Done/ with today's date> |
| Total This Month | <total Done count this month> |
```

### 3. Revenue (This Month)
Sum `total_revenue` from frontmatter of all batch files created this month:
```markdown
## Revenue (This Month)
- **Total Revenue**: $<sum>
- **Orders Paid**: <count where financial_status=paid>
- **Orders Pending Payment**: <count where financial_status=pending>
- **Refunds**: $0.00
```

### 4. Alerts
Check Business_Goals.md thresholds. Generate an alert line for each breach:
```markdown
## Alerts
- URGENT: 3 orders in /Needs_Action/ awaiting review
- WARNING: 2 orders unfulfilled for more than 48 hours
```
If nothing to flag: write `_No alerts. All clear._`

### 5. Recent Activity
List the 5 most recent actions (from batch file names and timestamps):
```markdown
## Recent Activity
- [2026-02-21 10:30] Processed 12 orders — $845.00 revenue
- [2026-02-21 09:00] 2 urgent orders routed to /Needs_Action/
```

### 6. Needs Action
List file names and summaries from `/Needs_Action/`:
```markdown
## Needs Action
- ORDERS_URGENT_2026-02-21_10-00.md — 2 high-priority orders
```
If empty: write `_Nothing pending._`

## Alert Threshold Rules

Read thresholds from `Business_Goals.md`. Defaults:
- Needs_Action folder has > 0 files: always alert
- Any order unfulfilled > 48h: WARNING
- Pending payment orders > 2: WARNING
- Revenue below 50% of monthly goal by mid-month: INFO
