---
name: order-reader
description: Reads and processes Shopify order CSV files from the E-commerce vault. Use when new order files appear in /Orders/ or /Needs_Action/, when the file watcher drops a new CSV, or when asked to "process orders" or "check new orders". Parses Shopify CSV exports, classifies orders by priority, creates structured summary .md files, and routes them to /Inbox/ (normal) or /Needs_Action/ (high priority). Also triggers dashboard-updater after processing.
---

# Order Reader

## Overview

Parses Shopify order CSV exports, classifies each order by priority rules from Company_Handbook.md, writes structured summaries to the vault, and routes files to the correct folder.

## Workflow

1. Read the CSV from `/Orders/` or `/Needs_Action/`
2. Run `scripts/parse_orders.py` to extract order data
3. Classify orders using priority rules (see below)
4. Write summary `.md` to `/Inbox/` (normal) or `/Needs_Action/` (high priority)
5. Move original CSV to `/Done/`
6. Update Dashboard.md using the `dashboard-updater` skill

## Running the Parser

```bash
python "E:/AI_Employee_Vault/.claude/skills/order-reader/scripts/parse_orders.py" \
  --input "E:/AI_Employee_Vault/Orders/<filename>.csv" \
  --vault "E:/AI_Employee_Vault"
```

## Priority Classification

Read `Company_Handbook.md` first. Default rules:

| Condition | Priority | Destination |
|-----------|----------|-------------|
| Order total > $100 | High | /Needs_Action/ |
| financial_status = pending | High | /Needs_Action/ |
| fulfillment_status = unfulfilled AND age > 48h | High | /Needs_Action/ |
| Customer note contains complaint/refund/cancel | High | /Needs_Action/ |
| Paid + unfulfilled (normal) | Normal | /Inbox/ |
| Paid + fulfilled | Done | /Done/ |

## Output File Format

Write one summary `.md` per batch:

```
/Inbox/ORDERS_YYYY-MM-DD_HH-MM.md
/Needs_Action/ORDERS_URGENT_YYYY-MM-DD_HH-MM.md
```

Template:

```markdown
---
type: order_batch
source_file: orders_export.csv
processed: 2026-02-21T10:30:00
order_count: 12
total_revenue: $845.00
priority: normal
status: pending
---

## Order Batch Summary
- Orders: 12 | Revenue: $845.00 | Needs Fulfillment: 8 | Payment Pending: 1

## Order List
| Order # | Customer | Items | Total | Payment | Fulfillment |
|---------|----------|-------|-------|---------|-------------|
| #1001   | Jane D.  | 2     | $45   | paid    | unfulfilled |

## Action Required
- [ ] Review and fulfil pending orders
- [ ] Follow up on pending payment: Order #XXXX
```

## Error Handling

- Malformed/empty CSV: write `ERROR_<filename>.md` to `/Needs_Action/`, do not move original
- Missing Company_Handbook.md: use default rules above, log warning in Dashboard
- Never delete original CSV without explicit confirmation

## References

- `references/shopify_columns.md` — full Shopify CSV column reference
