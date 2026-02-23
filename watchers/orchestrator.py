#!/usr/bin/env python3
"""
Orchestrator — Master Process for E-commerce AI Employee.

Responsibilities (per hackathon blueprint Section 5):
  1. PROCESS MANAGEMENT  — starts and keeps all watchers alive (Watchdog)
  2. FOLDER WATCHING     — monitors /Needs_Action/ and routes files to handlers
  3. SCHEDULING          — triggers daily briefing at 20:00 and weekly CEO brief on Sunday
  4. HEALTH MONITORING   — detects crashed watchers and restarts them
  5. AUDIT LOGGING       — JSON logs every orchestration action (Section 6.3)

Usage:
    python orchestrator.py
    python orchestrator.py --dry-run
    python orchestrator.py --no-watchers   (skip watcher management, only schedule)

Architecture:
    Orchestrator
    ├── WatcherManager  → starts/restarts gmail_watcher, orders_watcher, approval_watcher
    ├── FolderRouter    → detects new files in /Needs_Action/, routes by prefix
    └── Scheduler       → daily 20:00 briefing + Sunday CEO briefing
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from threading import Thread

# ── Config ────────────────────────────────────────────────────────────────────
VAULT_PATH = Path(os.getenv("VAULT_PATH", "E:/AI_Employee_Vault"))
WATCHERS_DIR = Path(__file__).parent
SCRIPTS = {
    "gmail_watcher": str(WATCHERS_DIR / "gmail_watcher.py"),
    "orders_watcher": str(WATCHERS_DIR / "orders_watcher.py"),
    "approval_watcher": str(WATCHERS_DIR / "approval_watcher.py"),
}

DAILY_BRIEFING_HOUR = 20    # 8 PM
WEEKLY_CEO_DAY = 6           # Sunday (0=Mon … 6=Sun)

LOGS_DIR = VAULT_PATH / "Logs"
NEEDS_ACTION = VAULT_PATH / "Needs_Action"

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] Orchestrator: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("Orchestrator")


def add_file_logger():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(
        LOGS_DIR / f"orchestrator_{datetime.now().strftime('%Y-%m')}.log",
        encoding="utf-8",
    )
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(fh)


def write_audit_log(action_type: str, target: str, result: str, **kwargs):
    """Append JSON audit entry to /Logs/YYYY-MM-DD.json (Section 6.3 format)."""
    date = datetime.now().strftime("%Y-%m-%d")
    log_file = LOGS_DIR / f"{date}.json"
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action_type": action_type,
        "actor": "Orchestrator",
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


# ── WatcherManager ────────────────────────────────────────────────────────────
class WatcherManager:
    """Starts and monitors watcher subprocesses. Restarts on crash."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.processes: dict[str, subprocess.Popen] = {}

    def start_watcher(self, name: str, script: str):
        if self.dry_run:
            logger.info(f"[DRY RUN] Would start: {name}")
            return
        logger.info(f"Starting {name}...")
        try:
            env = {**os.environ, "VAULT_PATH": str(VAULT_PATH)}
            proc = subprocess.Popen(
                [sys.executable, script],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            self.processes[name] = proc
            write_audit_log("watcher_started", name, "success", pid=proc.pid)
            logger.info(f"{name} started (PID {proc.pid})")
        except Exception as e:
            logger.error(f"Failed to start {name}: {e}")
            write_audit_log("watcher_start_failed", name, "error", error=str(e))

    def start_all(self):
        for name, script in SCRIPTS.items():
            if Path(script).exists():
                self.start_watcher(name, script)
            else:
                logger.warning(f"Script not found, skipping: {script}")

    def check_health(self):
        """Detect crashed processes and restart them."""
        for name, proc in list(self.processes.items()):
            if proc.poll() is not None:  # process exited
                exit_code = proc.returncode
                logger.warning(f"{name} exited (code {exit_code}). Restarting...")
                write_audit_log(
                    "watcher_crashed", name, "restarting",
                    exit_code=exit_code
                )
                self.start_watcher(name, SCRIPTS[name])

    def stop_all(self):
        for name, proc in self.processes.items():
            proc.terminate()
            logger.info(f"Stopped {name}")
        self.processes.clear()


# ── FolderRouter ──────────────────────────────────────────────────────────────
class FolderRouter:
    """
    Watches /Needs_Action/ and logs new files by type.
    Claude Code picks up these files via skills — the router just tracks them.
    """

    def __init__(self):
        self.seen_files: set = set()
        self._load_seen()

    def _seen_file(self) -> Path:
        return LOGS_DIR / "orchestrator_seen_files.json"

    def _load_seen(self):
        f = self._seen_file()
        if f.exists():
            try:
                self.seen_files = set(json.loads(f.read_text()))
            except Exception:
                pass

    def _save_seen(self):
        self._seen_file().write_text(
            json.dumps(list(self.seen_files)), encoding="utf-8"
        )

    def _route(self, filename: str) -> str:
        """Return the skill/handler that should process this file."""
        if filename.startswith("EMAIL_"):
            return "email-responder"
        if filename.startswith("ORDERS_") or filename.startswith("NEW_ORDERS_"):
            return "order-reader"
        if filename.startswith("LINKEDIN_"):
            return "linkedin-poster"
        if filename.startswith("PLAN_"):
            return "plan-creator"
        return "unknown"

    def scan(self):
        """Scan /Needs_Action/ for new files and log routing suggestions."""
        if not NEEDS_ACTION.exists():
            return

        for f in NEEDS_ACTION.iterdir():
            if f.name in self.seen_files or not f.is_file():
                continue

            skill = self._route(f.name)
            logger.info(f"New file detected: {f.name} -> route to [{skill}]")
            write_audit_log(
                action_type="file_detected",
                target=f.name,
                result="routed",
                skill=skill,
            )
            self.seen_files.add(f.name)

        self._save_seen()


# ── Scheduler ─────────────────────────────────────────────────────────────────
class Scheduler:
    """Triggers daily briefing at 20:00 and CEO briefing every Sunday."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self._last_daily: str = ""
        self._last_ceo: str = ""
        self.daily_script = WATCHERS_DIR / "daily_summary.py"

    def _today(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def _should_run_daily(self) -> bool:
        now = datetime.now()
        return (
            now.hour == DAILY_BRIEFING_HOUR
            and self._last_daily != self._today()
        )

    def _should_run_ceo(self) -> bool:
        now = datetime.now()
        return (
            now.weekday() == WEEKLY_CEO_DAY
            and now.hour == DAILY_BRIEFING_HOUR
            and self._last_ceo != self._today()
        )

    def run_daily_briefing(self):
        logger.info("Triggering daily briefing...")
        if self.dry_run:
            logger.info("[DRY RUN] Would run daily_summary.py")
            self._last_daily = self._today()
            return
        try:
            result = subprocess.run(
                [sys.executable, str(self.daily_script)],
                capture_output=True, text=True, timeout=120,
                env={**os.environ, "VAULT_PATH": str(VAULT_PATH)},
            )
            if result.returncode == 0:
                logger.info("Daily briefing completed.")
                write_audit_log("daily_briefing", "daily_summary.py", "success")
            else:
                logger.error(f"Daily briefing failed: {result.stderr}")
                write_audit_log("daily_briefing", "daily_summary.py", "error", stderr=result.stderr)
        except Exception as e:
            logger.error(f"Daily briefing error: {e}")
        self._last_daily = self._today()

    def run_ceo_briefing(self):
        """Generate Monday Morning CEO Briefing (Section 4)."""
        logger.info("Triggering weekly CEO briefing...")
        briefings_dir = VAULT_PATH / "Briefings"
        briefings_dir.mkdir(exist_ok=True)

        date_str = datetime.now().strftime("%Y-%m-%d")
        briefing_file = briefings_dir / f"{date_str}_Monday_Briefing.md"

        # Gather stats from vault
        done_files = list((VAULT_PATH / "Done").glob("*.md")) if (VAULT_PATH / "Done").exists() else []
        needs_action = list(NEEDS_ACTION.glob("*.md")) if NEEDS_ACTION.exists() else []
        pending = list((VAULT_PATH / "Pending_Approval").glob("*.md")) if (VAULT_PATH / "Pending_Approval").exists() else []

        # Count email vs order files in Done this week
        email_done = [f for f in done_files if f.name.startswith("EMAIL_")]
        order_done = [f for f in done_files if f.name.startswith("ORDERS_")]

        content = f"""---
generated: {datetime.now().isoformat()}
period: Weekly CEO Briefing
type: ceo_briefing
---

# Monday Morning CEO Briefing
*Generated by E-commerce AI Employee — {date_str}*

## Executive Summary
Weekly audit of store operations, communications, and pending items.

## Operations This Week
- Emails handled: {len(email_done)}
- Order batches processed: {len(order_done)}
- Items still pending approval: {len(pending)}
- Items awaiting action: {len(needs_action)}

## Completed Tasks
{chr(10).join(f'- [x] {f.name}' for f in done_files[-10:]) or '- No completed tasks this week'}

## Pending Approval
{chr(10).join(f'- [ ] {f.name}' for f in pending) or '- Nothing pending approval'}

## Bottlenecks / Needs Action
{chr(10).join(f'- {f.name}' for f in needs_action) or '- No pending items'}

## Proactive Suggestions
- Review any orders older than 48h in /Needs_Action/
- Check LinkedIn token expiry (tokens expire every 60 days)
- Verify Shopify CSV exports are being dropped to /Orders/

---
*Review the full logs at: {VAULT_PATH}/Logs/*
"""
        if not self.dry_run:
            briefing_file.write_text(content, encoding="utf-8")
            write_audit_log("ceo_briefing", str(briefing_file.name), "success")
            logger.info(f"CEO briefing written: {briefing_file.name}")
        else:
            logger.info(f"[DRY RUN] Would write CEO briefing: {briefing_file.name}")

        self._last_ceo = self._today()

    def tick(self):
        """Call this every minute to check if scheduled tasks should run."""
        if self._should_run_ceo():
            self.run_ceo_briefing()
        elif self._should_run_daily():
            self.run_daily_briefing()


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="E-commerce AI Employee Orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Log actions without executing")
    parser.add_argument("--no-watchers", action="store_true", help="Skip watcher process management")
    parser.add_argument("--vault", default=str(VAULT_PATH), help="Vault path")
    args = parser.parse_args()

    add_file_logger()

    logger.info("=" * 60)
    logger.info("E-commerce AI Employee Orchestrator starting")
    logger.info(f"Vault: {VAULT_PATH}")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info("=" * 60)

    watcher_mgr = WatcherManager(dry_run=args.dry_run)
    folder_router = FolderRouter()
    scheduler = Scheduler(dry_run=args.dry_run)

    # Start all watchers
    if not args.no_watchers:
        watcher_mgr.start_all()

    write_audit_log("orchestrator_started", "orchestrator.py", "success",
                    dry_run=args.dry_run, no_watchers=args.no_watchers)

    try:
        tick = 0
        while True:
            # Health check every 60s
            if not args.no_watchers:
                watcher_mgr.check_health()

            # Scan /Needs_Action/ for new files
            folder_router.scan()

            # Check scheduled tasks every 60s
            scheduler.tick()

            tick += 1
            time.sleep(60)

    except KeyboardInterrupt:
        logger.info("Shutting down...")
        watcher_mgr.stop_all()
        write_audit_log("orchestrator_stopped", "orchestrator.py", "success")
        logger.info("Orchestrator stopped.")


if __name__ == "__main__":
    main()
