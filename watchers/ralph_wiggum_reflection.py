#!/usr/bin/env python3
"""
Ralph Wiggum Self-Reflection Loop — E-commerce AI Employee (Gold Tier)

Reads the last 7 days of audit logs, analyses system performance, and writes
a structured reflection report to /Briefings/REFLECTION_YYYY-MM-DD.md.

Named after the Simpsons character whose naive observations reveal deeper truths —
this loop makes the AI employee self-aware: it knows what it did, what failed,
and what to improve.

Usage:
    python ralph_wiggum_reflection.py --vault E:/AI_Employee_Vault
    python ralph_wiggum_reflection.py --vault E:/AI_Employee_Vault --dry-run
"""

import argparse
import json
import os
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path


def load_logs(logs_dir: Path, days_back: int) -> list[dict]:
    """Load all audit log entries from the last N days."""
    entries = []
    today = date.today()
    for i in range(days_back):
        day = today - timedelta(days=i)
        log_file = logs_dir / f"{day.strftime('%Y-%m-%d')}.json"
        if log_file.exists():
            try:
                data = json.loads(log_file.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    entries.extend(data)
            except (json.JSONDecodeError, OSError):
                pass
    return entries


def get_log_days(logs_dir: Path, days_back: int) -> list[date]:
    """Return list of dates in window that have log files."""
    today = date.today()
    found = []
    for i in range(days_back):
        day = today - timedelta(days=i)
        if (logs_dir / f"{day.strftime('%Y-%m-%d')}.json").exists():
            found.append(day)
    return found


def analyse_action_success(entries: list[dict]) -> dict:
    """Per action_type: count success vs error. Flag >20% error rate."""
    counts: dict[str, dict] = defaultdict(lambda: {"success": 0, "error": 0, "total": 0})
    for e in entries:
        atype = e.get("action_type", "unknown")
        result = e.get("result", "")
        counts[atype]["total"] += 1
        if result in ("success", "routed", "no_reply_needed"):
            counts[atype]["success"] += 1
        elif result in ("error", "failed", "restarting"):
            counts[atype]["error"] += 1
        else:
            counts[atype]["success"] += 1  # treat unknown as success
    flagged = {
        atype: data for atype, data in counts.items()
        if data["total"] > 0 and data["error"] / data["total"] > 0.20
    }
    total_success = sum(d["success"] for d in counts.values())
    total_all = sum(d["total"] for d in counts.values())
    overall_pct = (total_success / total_all * 100) if total_all else 100.0
    return {
        "by_type": dict(counts),
        "flagged": flagged,
        "overall_pct": overall_pct,
        "total": total_all,
    }


def analyse_watcher_health(entries: list[dict]) -> dict:
    """Count watcher_crashed events per watcher. Flag if any crashed >2x."""
    crashes: dict[str, int] = defaultdict(int)
    for e in entries:
        if e.get("action_type") == "watcher_crashed":
            target = e.get("target", "unknown")
            crashes[target] += 1
    flagged = {name: count for name, count in crashes.items() if count > 2}
    return {
        "crashes": dict(crashes),
        "flagged": flagged,
        "total_crashes": sum(crashes.values()),
    }


def analyse_email_filter(entries: list[dict]) -> dict:
    """Ratio of email_batch_classified (blocked) vs action_file_created (passed)."""
    blocked = sum(
        e.get("count", 1)
        for e in entries
        if e.get("action_type") == "email_batch_classified"
        and e.get("result") == "no_reply_needed"
    )
    passed = sum(
        1 for e in entries
        if e.get("action_type") == "action_file_created"
        and str(e.get("target", "")).startswith("EMAIL_")
    )
    total = blocked + passed
    block_pct = (blocked / total * 100) if total else 0.0
    return {
        "blocked": blocked,
        "passed": passed,
        "total": total,
        "block_pct": block_pct,
    }


def analyse_stuck_items(vault: Path) -> dict:
    """Scan Pending_Approval (>24h) and Needs_Action (>48h) for stuck files."""
    now = datetime.now().timestamp()
    pending_stuck = []
    needs_stuck = []

    pending_dir = vault / "Pending_Approval"
    if pending_dir.exists():
        for f in pending_dir.iterdir():
            if f.is_file():
                age_hours = (now - f.stat().st_mtime) / 3600
                if age_hours > 24:
                    pending_stuck.append({"name": f.name, "age_hours": round(age_hours, 1)})

    needs_dir = vault / "Needs_Action"
    if needs_dir.exists():
        for f in needs_dir.iterdir():
            if f.is_file():
                age_hours = (now - f.stat().st_mtime) / 3600
                if age_hours > 48:
                    needs_stuck.append({"name": f.name, "age_hours": round(age_hours, 1)})

    return {
        "pending_stuck": pending_stuck,
        "needs_stuck": needs_stuck,
        "pending_count": len(pending_stuck),
        "needs_count": len(needs_stuck),
    }


def analyse_throughput(logs_dir: Path, days_back: int) -> dict:
    """Total actions processed per day. Detect trend."""
    today = date.today()
    daily_counts = {}
    for i in range(days_back):
        day = today - timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        log_file = logs_dir / f"{day_str}.json"
        if log_file.exists():
            try:
                data = json.loads(log_file.read_text(encoding="utf-8"))
                daily_counts[day_str] = len(data) if isinstance(data, list) else 0
            except (json.JSONDecodeError, OSError):
                daily_counts[day_str] = 0

    values = list(daily_counts.values())
    if len(values) >= 2:
        recent_avg = sum(values[:3]) / min(3, len(values))
        older_avg = sum(values[3:]) / max(1, len(values) - 3)
        trend = "up" if recent_avg > older_avg else ("flat" if recent_avg == older_avg else "down")
    else:
        trend = "insufficient data"

    return {"daily": daily_counts, "trend": trend}


def find_dead_days(logs_dir: Path, days_back: int) -> list[str]:
    """Days with zero log entries (orchestrator wasn't running)."""
    today = date.today()
    dead = []
    for i in range(days_back):
        day = today - timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        log_file = logs_dir / f"{day_str}.json"
        if not log_file.exists():
            dead.append(day_str)
        else:
            try:
                data = json.loads(log_file.read_text(encoding="utf-8"))
                if not data:
                    dead.append(day_str)
            except (json.JSONDecodeError, OSError):
                dead.append(day_str)
    return dead


def build_recommendations(
    watcher_health: dict,
    stuck: dict,
    email_filter: dict,
    action_success: dict,
) -> list[str]:
    recs = []

    if watcher_health["flagged"]:
        for name, count in watcher_health["flagged"].items():
            recs.append(
                f"**{name}** crashed {count}x — consider running orchestrator under PM2 for auto-restart"
            )

    if stuck["pending_count"] > 3:
        recs.append(
            f"{stuck['pending_count']} items in /Pending_Approval/ have been waiting >24h — review needed"
        )
    elif stuck["pending_count"] > 0:
        recs.append(
            f"{stuck['pending_count']} item(s) in /Pending_Approval/ awaiting review (>24h)"
        )

    if stuck["needs_count"] > 0:
        recs.append(
            f"{stuck['needs_count']} item(s) in /Needs_Action/ stuck >48h — may need manual processing"
        )

    if email_filter["total"] > 0 and email_filter["block_pct"] == 100.0 and email_filter["total"] > 5:
        recs.append(
            "All emails blocked (100%) — verify SENDER_BLOCKLIST isn't too aggressive"
        )

    error_pct_file_created = 0.0
    if "action_file_created" in action_success["by_type"]:
        d = action_success["by_type"]["action_file_created"]
        if d["total"] > 0:
            error_pct_file_created = d["error"] / d["total"] * 100
    if error_pct_file_created > 10:
        recs.append(
            f"Gmail API errors detected on action_file_created ({error_pct_file_created:.0f}% error rate) — check token expiry"
        )

    if not recs:
        recs.append("No actionable recommendations — system is healthy!")

    return recs


def score_system(
    watcher_health: dict,
    stuck: dict,
    action_success: dict,
    dead_days: list,
) -> str:
    """GREEN | YELLOW | RED"""
    if (
        watcher_health["flagged"]
        or action_success["overall_pct"] < 80
        or len(dead_days) > 3
    ):
        return "RED"
    if (
        watcher_health["total_crashes"] > 0
        or stuck["pending_count"] > 1
        or stuck["needs_count"] > 0
        or action_success["overall_pct"] < 95
        or len(dead_days) > 0
    ):
        return "YELLOW"
    return "GREEN"


def score_area(condition_green: bool, condition_yellow: bool = False) -> str:
    if condition_green:
        return "GREEN"
    if condition_yellow:
        return "YELLOW"
    return "RED"


def generate_reflection(vault: Path, days_back: int) -> str:
    today = date.today()
    today_str = today.strftime("%Y-%m-%d")
    today_display = today.strftime("%b %d, %Y")
    now_iso = datetime.now().isoformat()

    logs_dir = vault / "Logs"

    entries = load_logs(logs_dir, days_back)
    action_success = analyse_action_success(entries)
    watcher_health = analyse_watcher_health(entries)
    email_filter = analyse_email_filter(entries)
    stuck = analyse_stuck_items(vault)
    throughput = analyse_throughput(logs_dir, days_back)
    dead_days = find_dead_days(logs_dir, days_back)
    recommendations = build_recommendations(watcher_health, stuck, email_filter, action_success)

    overall_score = score_system(watcher_health, stuck, action_success, dead_days)

    # Scorecard area scores
    stability_green = watcher_health["total_crashes"] == 0
    stability_yellow = not stability_green and not watcher_health["flagged"]
    stability_score = score_area(stability_green, stability_yellow)
    stability_detail = (
        f"{watcher_health['total_crashes']} crash(es) in {days_back} days"
        if watcher_health["total_crashes"]
        else f"0 crashes in {days_back} days"
    )

    ef = email_filter
    filter_score = score_area(
        ef["total"] == 0 or (0 < ef["block_pct"] < 100),
        ef["block_pct"] == 100 and ef["total"] <= 5,
    )
    filter_detail = (
        f"{ef['blocked']} blocked, {ef['passed']} passed through"
        if ef["total"] > 0
        else "No emails processed"
    )

    lag_score = score_area(
        stuck["pending_count"] == 0,
        stuck["pending_count"] <= 3,
    )
    lag_detail = (
        f"{stuck['pending_count']} item(s) >24h in /Pending_Approval/"
        if stuck["pending_count"]
        else "No approval lag"
    )

    success_pct = action_success["overall_pct"]
    success_score = score_area(success_pct >= 95, success_pct >= 80)
    success_detail = f"{success_pct:.0f}% success rate ({action_success['total']} total actions)"

    # Quote flavour
    quote_map = {
        "GREEN": '"I\'m a helper!" — Overall system health: GREEN',
        "YELLOW": '"I didn\'t do it." — Some things need attention: YELLOW',
        "RED": '"My cat\'s breath smells like cat food." — System needs help: RED',
    }
    quote = quote_map[overall_score]

    # Went well / needs attention
    went_well = []
    needs_attention = []

    if stability_score == "GREEN":
        went_well.append(f"Watchers ran stably — {stability_detail}")
    else:
        needs_attention.append(f"Watcher instability — {stability_detail}")

    if filter_score == "GREEN":
        went_well.append(f"Email filter operating normally — {filter_detail}")
    elif filter_score == "YELLOW":
        needs_attention.append(f"Email filter may be over-blocking — {filter_detail}")
    else:
        needs_attention.append(f"Email filter issue — {filter_detail}")

    if lag_score == "GREEN":
        went_well.append("No items stuck in approval queue")
    else:
        needs_attention.append(f"Approval lag detected — {lag_detail}")

    if success_score == "GREEN":
        went_well.append(f"High action success rate — {success_detail}")
    else:
        needs_attention.append(f"Action errors detected — {success_detail}")

    if not dead_days:
        went_well.append(f"Orchestrator ran every day in the {days_back}-day window")
    else:
        needs_attention.append(f"{len(dead_days)} dead day(s) (no logs): {', '.join(dead_days)}")

    if not went_well:
        went_well.append("Nothing stood out as particularly good this period.")
    if not needs_attention:
        needs_attention.append("Nothing requires attention — all clear!")

    went_well_md = "\n".join(f"- {item}" for item in went_well)
    needs_attention_md = "\n".join(f"- {item}" for item in needs_attention)
    recommendations_md = "\n".join(f"- [ ] {rec}" for rec in recommendations)

    # Throughput table
    throughput_rows = ""
    for day_str in sorted(throughput["daily"].keys(), reverse=True):
        count = throughput["daily"][day_str]
        throughput_rows += f"| {day_str} | {count} |\n"
    if not throughput_rows:
        throughput_rows = "| (no data) | — |\n"

    # Dead days section
    dead_days_md = ", ".join(dead_days) if dead_days else "None — orchestrator ran every day"

    # Action type breakdown
    action_rows = ""
    for atype, data in sorted(action_success["by_type"].items()):
        err_pct = (data["error"] / data["total"] * 100) if data["total"] else 0
        flag = " ⚠" if atype in action_success["flagged"] else ""
        action_rows += f"| {atype}{flag} | {data['total']} | {data['success']} | {data['error']} | {err_pct:.0f}% |\n"
    if not action_rows:
        action_rows = "| (no actions logged) | — | — | — | — |\n"

    report = f"""---
type: reflection
period: {days_back} days
generated: {now_iso}
score: {overall_score}
---

# Ralph Wiggum Self-Reflection — {today_display}
*{quote}*

## Performance Scorecard
| Area              | Score  | Detail |
|---|---|---|
| Watcher stability | {stability_score}  | {stability_detail} |
| Email filter      | {filter_score}  | {filter_detail} |
| Approval lag      | {lag_score}  | {lag_detail} |
| Action success    | {success_score}  | {success_detail} |

## What Went Well
{went_well_md}

## What Needs Attention
{needs_attention_md}

## Recommendations
{recommendations_md}

## Raw Stats (Last {days_back} Days)

### Throughput (actions per day)
| Date | Actions |
|---|---|
{throughput_rows}
Trend: {throughput["trend"]}

### Dead Days (no log entries)
{dead_days_md}

### Action Type Breakdown
| Action Type | Total | Success | Errors | Error % |
|---|---|---|---|---|
{action_rows}
### Email Filter
- Emails blocked (non-customer): {ef['blocked']}
- Emails passed (customer): {ef['passed']}
- Block rate: {ef['block_pct']:.1f}%

### Watcher Crashes (last {days_back} days)
{json.dumps(watcher_health['crashes'], indent=2) if watcher_health['crashes'] else '(none)'}

---
*Generated by Ralph Wiggum Reflection Loop at {now_iso}*
"""
    return report


def write_audit_log(logs_dir: Path, action_type: str, target: str, result: str, **kwargs):
    """Append JSON audit entry to /Logs/YYYY-MM-DD.json."""
    logs_dir.mkdir(parents=True, exist_ok=True)
    day_str = datetime.now().strftime("%Y-%m-%d")
    log_file = logs_dir / f"{day_str}.json"
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action_type": action_type,
        "actor": "RalphWiggumReflection",
        "target": target,
        "result": result,
        **kwargs,
    }
    existing = []
    if log_file.exists():
        try:
            existing = json.loads(log_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    existing.append(entry)
    log_file.write_text(json.dumps(existing, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Ralph Wiggum Self-Reflection Loop")
    parser.add_argument("--vault", default=os.getenv("VAULT_PATH", "E:/AI_Employee_Vault"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--days",
        type=int,
        default=int(os.getenv("REFLECTION_DAYS_BACK", "7")),
        help="Number of days to look back (default: 7)",
    )
    args = parser.parse_args()

    vault = Path(args.vault)
    briefings_dir = vault / "Briefings"
    logs_dir = vault / "Logs"

    content = generate_reflection(vault, args.days)

    out_path = briefings_dir / f"REFLECTION_{date.today().strftime('%Y-%m-%d')}.md"

    if args.dry_run:
        print("[DRY RUN] Would write:")
        print(content)
    else:
        briefings_dir.mkdir(exist_ok=True)
        out_path.write_text(content, encoding="utf-8")
        print(f"[OK] Reflection report written: {out_path}")
        write_audit_log(
            logs_dir,
            "reflection_generated",
            out_path.name,
            "success",
            days_back=args.days,
        )


if __name__ == "__main__":
    main()
