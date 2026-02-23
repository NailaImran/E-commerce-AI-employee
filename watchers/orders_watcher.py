#!/usr/bin/env python3
"""
Orders Folder Watcher — E-commerce AI Employee (Bronze Tier)

Monitors E:/AI_Employee_Vault/Orders/ for new Shopify CSV exports.
When a new file is detected, it creates a metadata .md file in /Needs_Action/
so Claude Code knows to process it.

Usage:
    python orders_watcher.py
    python orders_watcher.py --vault E:/AI_Employee_Vault
    python orders_watcher.py --vault E:/AI_Employee_Vault --auto-parse

Requirements:
    pip install watchdog

Run persistently with PM2:
    pm2 start orders_watcher.py --interpreter python3 --name orders-watcher
    pm2 save
    pm2 startup
"""

import argparse
import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
except ImportError:
    print("[ERROR] watchdog not installed. Run: pip install watchdog")
    sys.exit(1)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("OrdersWatcher")


class OrdersDropHandler(FileSystemEventHandler):
    """Handles new files dropped into the /Orders/ folder."""

    SUPPORTED_EXTENSIONS = {".csv", ".tsv"}

    def __init__(self, vault_path: Path, auto_parse: bool = False):
        self.vault = vault_path
        self.needs_action = vault_path / "Needs_Action"
        self.needs_action.mkdir(exist_ok=True)
        self.auto_parse = auto_parse
        self.parse_script = Path(__file__).parent.parent / "skills" / "order-reader" / "scripts" / "parse_orders.py"

    def on_created(self, event):
        if event.is_directory:
            return
        source = Path(event.src_path)
        if source.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            logger.info(f"Skipping non-CSV file: {source.name}")
            return

        logger.info(f"New order file detected: {source.name}")
        self._create_trigger_file(source)

        if self.auto_parse:
            self._run_parser(source)

    def _create_trigger_file(self, source: Path):
        """Create a .md trigger file in /Needs_Action/ for Claude to pick up."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        trigger_path = self.needs_action / f"NEW_ORDERS_{source.stem}_{timestamp}.md"

        content = f"""---
type: new_order_file
source_file: {source.name}
source_path: {source}
detected: {datetime.now().isoformat()}
status: pending_processing
---

## New Shopify Order File Detected

A new order export has been dropped into the /Orders/ folder.

**File**: `{source.name}`
**Detected**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Instructions for Claude

1. Run the order-reader skill to process this file:
   ```
   python "{self.parse_script}" --input "{source}" --vault "{self.vault}"
   ```
2. After processing, run dashboard-updater:
   ```
   python "{self.vault.parent}/skills/dashboard-updater/scripts/update_dashboard.py" --vault "{self.vault}"
   ```
3. Move this trigger file to /Done/ when complete.
"""
        trigger_path.write_text(content, encoding="utf-8")
        logger.info(f"Trigger file created: {trigger_path.name}")

    def _run_parser(self, source: Path):
        """Auto-run the parse_orders.py script (auto-parse mode)."""
        if not self.parse_script.exists():
            logger.warning(f"Parser not found at {self.parse_script}")
            return

        logger.info(f"Auto-parsing: {source.name}")
        try:
            result = subprocess.run(
                [sys.executable, str(self.parse_script), "--input", str(source), "--vault", str(self.vault)],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                logger.info(f"Parser output: {result.stdout.strip()}")
            else:
                logger.error(f"Parser error: {result.stderr.strip()}")
        except subprocess.TimeoutExpired:
            logger.error("Parser timed out after 60 seconds")
        except Exception as e:
            logger.error(f"Failed to run parser: {e}")


def main():
    parser = argparse.ArgumentParser(description="Watch /Orders/ folder for new Shopify CSV exports")
    parser.add_argument(
        "--vault",
        default="E:/AI_Employee_Vault",
        help="Path to AI_Employee_Vault root (default: E:/AI_Employee_Vault)",
    )
    parser.add_argument(
        "--auto-parse",
        action="store_true",
        help="Automatically run parse_orders.py when a new file is detected",
    )
    args = parser.parse_args()

    vault = Path(args.vault)
    orders_folder = vault / "Orders"

    if not vault.exists():
        logger.error(f"Vault not found: {vault}")
        sys.exit(1)

    orders_folder.mkdir(exist_ok=True)
    logger.info(f"Watching: {orders_folder}")
    logger.info(f"Vault: {vault}")
    logger.info(f"Auto-parse: {args.auto_parse}")
    logger.info("Waiting for new Shopify CSV files... (Ctrl+C to stop)")

    # Add log file handler
    log_dir = vault / "Logs"
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(
        log_dir / f"orders_watcher_{datetime.now().strftime('%Y-%m')}.log",
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(file_handler)

    event_handler = OrdersDropHandler(vault, auto_parse=args.auto_parse)
    observer = Observer()
    observer.schedule(event_handler, str(orders_folder), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping watcher...")
        observer.stop()

    observer.join()
    logger.info("Watcher stopped.")


if __name__ == "__main__":
    main()
