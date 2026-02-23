---
name: plan-creator
description: Creates a structured Plan.md file for each order batch or task cluster in the E-commerce vault. Use when a new order batch has been processed, when asked to "create a plan", "make a plan for these orders", or after the order-reader skill runs. Reads order summary files and generates an actionable step-by-step plan with checkboxes, priorities, and deadlines written to /Plans/.
---

# Plan Creator

## Overview

Turns order batch summaries and needs-action items into structured Plan.md files with prioritised, checkbox-driven action steps stored in `/Plans/`.

## Workflow

1. Read the source order batch `.md` from `/Inbox/` or `/Needs_Action/`
2. Read `Company_Handbook.md` for processing rules
3. Generate a Plan.md with ordered action steps
4. Write to `/Plans/PLAN_<source_stem>_<date>.md`
5. Update Dashboard.md "Recent Activity" section

## Plan File Format

Write to `/Plans/PLAN_<batch_name>_<YYYY-MM-DD>.md`:

```markdown
---
type: order_plan
source_batch: ORDERS_2026-02-21_10-30.md
created: 2026-02-21T10:30:00
order_count: 12
total_revenue: $845.00
status: in_progress
---

## Objective
Process and fulfil 12 Shopify orders totalling $845.00 from batch ORDERS_2026-02-21.

## Priority Actions (Complete First)
- [ ] URGENT: Follow up on 2 pending payments (#1002, #1005)
- [ ] URGENT: Respond to complaint email from customer in Order #1008

## Fulfilment Steps
- [ ] Pack and dispatch 8 unfulfilled orders
- [ ] Mark as fulfilled in Shopify after dispatch
- [ ] Upload tracking numbers to Shopify

## Customer Communication
- [ ] Send shipping confirmation for dispatched orders
- [ ] Follow up on Order #1003 (unfulfilled > 48h)

## Financial
- [ ] Verify payment cleared for all paid orders
- [ ] Log revenue in Business_Goals.md MTD total

## Done Criteria
All orders fulfilled, payments confirmed, customers notified.
Move this file to /Done/ when complete.
```

## Step Priority Rules

Order steps as follows:
1. Payments pending or suspicious (always first)
2. Customer complaints / refund requests
3. Orders unfulfilled > 48h
4. Standard fulfilment (pack + ship)
5. Communication (confirmations, follow-ups)
6. Financial logging

## When to Create a Plan

- After every `order-reader` run (one Plan per batch file)
- When `/Needs_Action/` contains unplanned items
- When manually asked to plan a set of tasks

## Linking Plans to Batches

Always include `source_batch` in frontmatter so the orchestrator can trace Plan → Batch → Done.
