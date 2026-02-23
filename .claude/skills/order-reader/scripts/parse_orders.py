#!/usr/bin/env python3
"""
Shopify Order CSV Parser for E-commerce AI Employee (Bronze Tier)

Usage:
    python parse_orders.py --input <path/to/orders.csv> --vault <path/to/vault>

Output:
    - Creates .md summary in /Inbox/ or /Needs_Action/ depending on priority
    - Moves original CSV to /Done/
    - Prints JSON summary to stdout
"""

import argparse
import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


# Priority threshold (overridden by Company_Handbook.md if parsed)
HIGH_VALUE_THRESHOLD = 100.0
OLD_UNFULFILLED_HOURS = 48


def classify_order(row: dict) -> str:
    """Return 'high' or 'normal' priority for a single order row."""
    try:
        total = float(row.get("Total", "0").replace("$", "").replace(",", "") or 0)
    except ValueError:
        total = 0.0

    financial = row.get("Financial Status", "").strip().lower()
    fulfillment = row.get("Fulfillment Status", "").strip().lower()
    notes = row.get("Notes", "").strip().lower()
    created_at_str = row.get("Created at", "")

    if total > HIGH_VALUE_THRESHOLD:
        return "high"
    if financial == "pending":
        return "high"
    if any(kw in notes for kw in ["refund", "cancel", "complaint", "wrong", "broken", "missing"]):
        return "high"

    # Check age of unfulfilled orders
    if fulfillment in ("unfulfilled", "partial") and created_at_str:
        try:
            created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            age_hours = (datetime.now(timezone.utc) - created_at).total_seconds() / 3600
            if age_hours > OLD_UNFULFILLED_HOURS:
                return "high"
        except ValueError:
            pass

    return "normal"


def parse_csv(filepath: Path) -> list[dict]:
    """Parse Shopify CSV, return list of order row dicts."""
    orders = []
    with open(filepath, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip empty rows
            if not row.get("Name", "").strip():
                continue
            orders.append(dict(row))
    return orders


def build_summary_md(orders: list[dict], source_file: str, priority: str) -> str:
    """Build the markdown summary file content."""
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    total_revenue = sum(
        float(o.get("Total", "0").replace("$", "").replace(",", "") or 0)
        for o in orders
    )
    paid_count = sum(1 for o in orders if o.get("Financial Status", "").lower() == "paid")
    pending_count = sum(1 for o in orders if o.get("Financial Status", "").lower() == "pending")
    unfulfilled_count = sum(
        1 for o in orders if o.get("Fulfillment Status", "").lower() in ("unfulfilled", "partial")
    )

    rows = []
    for o in orders:
        name = o.get("Name", "")
        customer = o.get("Shipping Name", o.get("Email", "Unknown"))[:20]
        items = o.get("Lineitem quantity", "?")
        total = o.get("Total", "$0")
        fin = o.get("Financial Status", "")
        ful = o.get("Fulfillment Status", "")
        rows.append(f"| {name} | {customer} | {items} | {total} | {fin} | {ful} |")

    table_rows = "\n".join(rows) if rows else "| — | — | — | — | — | — |"

    action_items = []
    if unfulfilled_count:
        action_items.append(f"- [ ] Fulfil {unfulfilled_count} pending order(s)")
    if pending_count:
        action_items.append(f"- [ ] Follow up on {pending_count} payment(s) pending")
    if priority == "high":
        action_items.append("- [ ] Review high-priority orders above")
    if not action_items:
        action_items.append("- [ ] Review and confirm all orders")

    actions = "\n".join(action_items)

    return f"""---
type: order_batch
source_file: {source_file}
processed: {now}
order_count: {len(orders)}
total_revenue: ${total_revenue:.2f}
priority: {priority}
status: pending
---

## Order Batch Summary
- **Orders**: {len(orders)} | **Revenue**: ${total_revenue:.2f}
- **Paid**: {paid_count} | **Payment Pending**: {pending_count} | **Needs Fulfillment**: {unfulfilled_count}

## Order List
| Order # | Customer | Items | Total | Payment | Fulfillment |
|---------|----------|-------|-------|---------|-------------|
{table_rows}

## Action Required
{actions}
"""


def main():
    parser = argparse.ArgumentParser(description="Parse Shopify order CSV for AI Employee vault")
    parser.add_argument("--input", required=True, help="Path to Shopify orders CSV file")
    parser.add_argument("--vault", required=True, help="Path to AI_Employee_Vault root")
    parser.add_argument("--dry-run", action="store_true", help="Log actions without writing files")
    args = parser.parse_args()

    input_path = Path(args.input)
    vault = Path(args.vault)

    if not input_path.exists():
        print(json.dumps({"error": f"File not found: {input_path}"}))
        raise SystemExit(1)

    # Parse
    try:
        orders = parse_csv(input_path)
    except Exception as e:
        # Write error file
        error_md = vault / "Needs_Action" / f"ERROR_{input_path.name}.md"
        if not args.dry_run:
            error_md.write_text(f"---\ntype: parse_error\nfile: {input_path.name}\n---\n\nFailed to parse: {e}\n")
        print(json.dumps({"error": str(e)}))
        raise SystemExit(1)

    if not orders:
        print(json.dumps({"warning": "CSV contained no order rows", "file": str(input_path)}))
        raise SystemExit(0)

    # Classify batch priority: high if ANY order is high
    priorities = [classify_order(o) for o in orders]
    batch_priority = "high" if "high" in priorities else "normal"

    # Determine destination
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    if batch_priority == "high":
        dest_folder = vault / "Needs_Action"
        out_name = f"ORDERS_URGENT_{timestamp}.md"
    else:
        dest_folder = vault / "Inbox"
        out_name = f"ORDERS_{timestamp}.md"

    dest_folder.mkdir(exist_ok=True)
    out_path = dest_folder / out_name
    done_folder = vault / "Done"
    done_folder.mkdir(exist_ok=True)

    summary_md = build_summary_md(orders, input_path.name, batch_priority)

    if not args.dry_run:
        out_path.write_text(summary_md, encoding="utf-8")
        shutil.move(str(input_path), str(done_folder / input_path.name))
        print(f"[OK] Written: {out_path}")
        print(f"[OK] Moved original to: {done_folder / input_path.name}")
    else:
        print(f"[DRY RUN] Would write: {out_path}")
        print(f"[DRY RUN] Would move to: {done_folder / input_path.name}")

    result = {
        "order_count": len(orders),
        "total_revenue": sum(
            float(o.get("Total", "0").replace("$", "").replace(",", "") or 0) for o in orders
        ),
        "priority": batch_priority,
        "output_file": str(out_path),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
