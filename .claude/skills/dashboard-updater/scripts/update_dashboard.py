#!/usr/bin/env python3
"""
Dashboard Updater for E-commerce AI Employee (Bronze Tier)

Reads vault folder state and rewrites Dashboard.md with current metrics.

Usage:
    python update_dashboard.py --vault <path/to/AI_Employee_Vault>
    python update_dashboard.py --vault E:/AI_Employee_Vault --dry-run
"""

import argparse
import re
from datetime import datetime, date
from pathlib import Path


def count_orders_in_folder(folder: Path) -> tuple[int, float]:
    """Return (order_count, total_revenue) from .md batch files in folder."""
    total_orders = 0
    total_revenue = 0.0
    for md in folder.glob("ORDERS*.md"):
        text = md.read_text(encoding="utf-8", errors="ignore")
        m_count = re.search(r"order_count:\s*(\d+)", text)
        m_rev = re.search(r"total_revenue:\s*\$?([\d.]+)", text)
        if m_count:
            total_orders += int(m_count.group(1))
        if m_rev:
            total_revenue += float(m_rev.group(1))
    return total_orders, total_revenue


def count_done_today(done_folder: Path) -> int:
    """Count order batch files in /Done/ processed today."""
    today_str = date.today().strftime("%Y-%m-%d")
    return sum(1 for f in done_folder.glob(f"ORDERS*{today_str}*.md"))


def count_done_this_month(done_folder: Path) -> tuple[int, float]:
    """Count orders + revenue in /Done/ for current month."""
    month_str = date.today().strftime("%Y-%m")
    total_orders = 0
    total_revenue = 0.0
    for md in done_folder.glob(f"ORDERS*{month_str}*.md"):
        text = md.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"order_count:\s*(\d+)", text)
        r = re.search(r"total_revenue:\s*\$?([\d.]+)", text)
        if m:
            total_orders += int(m.group(1))
        if r:
            total_revenue += float(r.group(1))
    return total_orders, total_revenue


def build_alerts(vault: Path, needs_action_count: int) -> str:
    alerts = []
    if needs_action_count > 0:
        alerts.append(f"- URGENT: {needs_action_count} item(s) in /Needs_Action/ awaiting review")
    # Check for error files
    error_count = len(list((vault / "Needs_Action").glob("ERROR_*.md")))
    if error_count:
        alerts.append(f"- ERROR: {error_count} file(s) failed to parse — check /Needs_Action/ERROR_*")
    return "\n".join(alerts) if alerts else "_No alerts. All clear._"


def build_needs_action_list(needs_action_folder: Path) -> str:
    items = []
    for md in sorted(needs_action_folder.glob("*.md")):
        text = md.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"order_count:\s*(\d+)", text)
        count_str = f" — {m.group(1)} orders" if m else ""
        items.append(f"- {md.name}{count_str}")
    return "\n".join(items) if items else "_Nothing pending._"


def build_recent_activity(vault: Path, limit: int = 5) -> str:
    all_batches = []
    for folder in [vault / "Inbox", vault / "Needs_Action", vault / "Done"]:
        for md in folder.glob("ORDERS*.md"):
            all_batches.append(md)
    # Sort by modification time
    all_batches.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    lines = []
    for md in all_batches[:limit]:
        mtime = datetime.fromtimestamp(md.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        text = md.read_text(encoding="utf-8", errors="ignore")
        m_count = re.search(r"order_count:\s*(\d+)", text)
        m_rev = re.search(r"total_revenue:\s*\$?([\d.]+)", text)
        count_str = m_count.group(1) if m_count else "?"
        rev_str = f"${float(m_rev.group(1)):.2f}" if m_rev else "$?"
        priority = "URGENT" if "URGENT" in md.name else "normal"
        lines.append(f"- [{mtime}] [{priority}] {count_str} orders — {rev_str} revenue ({md.parent.name})")
    return "\n".join(lines) if lines else "_No activity yet._"


def update_dashboard(vault_path: str, dry_run: bool = False):
    vault = Path(vault_path)
    dashboard = vault / "Dashboard.md"

    if not dashboard.exists():
        print(f"[ERROR] Dashboard.md not found at {dashboard}")
        raise SystemExit(1)

    inbox = vault / "Inbox"
    needs_action = vault / "Needs_Action"
    done = vault / "Done"
    for folder in [inbox, needs_action, done]:
        folder.mkdir(exist_ok=True)

    inbox_orders, inbox_revenue = count_orders_in_folder(inbox)
    needs_action_count = len(list(needs_action.glob("*.md")))
    done_today = count_done_today(done)
    done_month_orders, done_month_revenue = count_done_this_month(done)

    # Total month revenue = done + inbox + needs_action
    _, na_revenue = count_orders_in_folder(needs_action)
    total_month_revenue = done_month_revenue + inbox_revenue + na_revenue

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    new_content = f"""---
last_updated: {now_str}
agent_version: 0.1-bronze
---

# E-commerce Store Dashboard

## Store Status
- **Platform**: Shopify
- **Agent Tier**: Bronze
- **Last Sync**: {now_str}

---

## Order Summary

| Metric | Count |
|--------|-------|
| New Orders (Inbox) | {inbox_orders} |
| Needs Action | {needs_action_count} |
| Completed Today | {done_today} |
| Total This Month | {done_month_orders} |

---

## Revenue (This Month)
- **Total Revenue**: ${total_month_revenue:.2f}
- **Orders in Inbox**: {inbox_orders} (${inbox_revenue:.2f})
- **Orders Completed**: {done_month_orders} (${done_month_revenue:.2f})

---

## Alerts
{build_alerts(vault, needs_action_count)}

---

## Recent Activity
{build_recent_activity(vault)}

---

## Needs Action
{build_needs_action_list(needs_action)}

---

*Managed by Claude Code AI Employee | Bronze Tier | Updated: {now_str}*
"""

    if dry_run:
        print("[DRY RUN] Would write Dashboard.md:")
        print(new_content)
    else:
        dashboard.write_text(new_content, encoding="utf-8")
        print(f"[OK] Dashboard.md updated at {now_str}")


def main():
    parser = argparse.ArgumentParser(description="Update E-commerce AI Employee Dashboard")
    parser.add_argument("--vault", required=True, help="Path to AI_Employee_Vault root")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()
    update_dashboard(args.vault, args.dry_run)


if __name__ == "__main__":
    main()
