#!/usr/bin/env python3
"""
Approval Watcher — E-commerce AI Employee (Silver Tier)

Monitors /Approved/ folder. When a file appears:
  - EMAIL_REPLY_*.md  → calls send_approved_email.py
  - LINKEDIN_*.md     → calls post_to_linkedin.py
  - Other             → logs and moves to /Done/

Usage:
    python approval_watcher.py --vault E:/AI_Employee_Vault
    python approval_watcher.py --vault E:/AI_Employee_Vault --dry-run

Run with PM2:
    pm2 start approval_watcher.py --interpreter python3 --name approval-watcher
"""

import argparse
import logging
import subprocess
import sys
import time
from pathlib import Path

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
except ImportError:
    print("[ERROR] Run: pip install watchdog")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ApprovalWatcher")

SKILLS_ROOT = Path("E:/E-commerce-employee/skills")


class ApprovalHandler(FileSystemEventHandler):
    def __init__(self, vault: Path, dry_run: bool = False):
        self.vault = vault
        self.dry_run = dry_run
        self.token_file = vault / ".secrets" / "linkedin_token.txt"

    def on_created(self, event):
        if event.is_directory:
            return
        filepath = Path(event.src_path)
        if filepath.suffix != ".md":
            return

        name = filepath.name
        logger.info(f"Approval detected: {name}")

        if name.startswith("EMAIL_REPLY_"):
            self._handle_email(filepath)
        elif name.startswith("LINKEDIN_"):
            self._handle_linkedin(filepath)
        else:
            logger.info(f"Unknown approval type: {name} — moving to /Done/")
            self._move_to_done(filepath)

    def _handle_email(self, filepath: Path):
        script = SKILLS_ROOT / "email-responder" / "scripts" / "send_approved_email.py"
        cmd = [sys.executable, str(script), "--file", str(filepath), "--vault", str(self.vault)]
        if self.dry_run:
            cmd.append("--dry-run")
        self._run(cmd, f"email send for {filepath.name}")

    def _handle_linkedin(self, filepath: Path):
        script = SKILLS_ROOT / "linkedin-poster" / "scripts" / "post_to_linkedin.py"
        cmd = [
            sys.executable, str(script),
            "--file", str(filepath),
            "--token-file", str(self.token_file),
            "--vault", str(self.vault),
        ]
        if self.dry_run:
            cmd.append("--dry-run")
        self._run(cmd, f"LinkedIn post for {filepath.name}")

    def _run(self, cmd: list, description: str):
        logger.info(f"Running: {description}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env={"PYTHONUTF8": "1", **__import__("os").environ})
            if result.returncode == 0:
                logger.info(f"Success: {description}\n{result.stdout.strip()}")
            else:
                logger.error(f"Failed: {description}\n{result.stderr.strip()}")
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout: {description}")
        except Exception as e:
            logger.error(f"Error running {description}: {e}")

    def _move_to_done(self, filepath: Path):
        done = self.vault / "Done"
        done.mkdir(exist_ok=True)
        filepath.rename(done / filepath.name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", default="E:/AI_Employee_Vault")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    vault = Path(args.vault)
    approved_dir = vault / "Approved"
    approved_dir.mkdir(exist_ok=True)

    logger.info(f"Watching: {approved_dir}")
    logger.info(f"Dry-run: {args.dry_run}")

    handler = ApprovalHandler(vault, args.dry_run)
    observer = Observer()
    observer.schedule(handler, str(approved_dir), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
