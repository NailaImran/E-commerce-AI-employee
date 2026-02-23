#!/usr/bin/env python3
"""
BaseWatcher — Abstract base class for all E-commerce AI Employee watchers.

All watchers inherit from this class and implement:
  - check_for_updates() → list of new items to process
  - create_action_file(item) → Path to .md file written in /Needs_Action/

The run() loop, logging, error handling, and retry logic are provided here.

Usage (in a subclass):
    class GmailWatcher(BaseWatcher):
        def check_for_updates(self): ...
        def create_action_file(self, item): ...

    if __name__ == "__main__":
        GmailWatcher(vault_path="E:/AI_Employee_Vault").run()
"""

import json
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path


class BaseWatcher(ABC):
    """Abstract base for all watchers. Provides run loop, logging, retry logic."""

    def __init__(
        self,
        vault_path: str = "E:/AI_Employee_Vault",
        check_interval: int = 60,
        max_retries: int = 3,
        retry_base_delay: int = 5,
    ):
        self.vault_path = Path(vault_path)
        self.needs_action = self.vault_path / "Needs_Action"
        self.done = self.vault_path / "Done"
        self.logs_dir = self.vault_path / "Logs"
        self.check_interval = check_interval
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay
        self._running = False

        # Ensure folders exist
        self.needs_action.mkdir(parents=True, exist_ok=True)
        self.done.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Set up logging — both stdout and file
        self.logger = logging.getLogger(self.__class__.__name__)
        if not self.logger.handlers:
            self.logger.setLevel(logging.INFO)
            fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

            sh = logging.StreamHandler()
            sh.setFormatter(fmt)
            self.logger.addHandler(sh)

            log_file = self.logs_dir / f"{self.__class__.__name__.lower()}_{datetime.now().strftime('%Y-%m')}.log"
            fh = logging.FileHandler(log_file, encoding="utf-8")
            fh.setFormatter(fmt)
            self.logger.addHandler(fh)

    # ── Abstract interface ────────────────────────────────────────────────────

    @abstractmethod
    def check_for_updates(self) -> list:
        """Poll the external source. Return a list of new items to process."""
        pass

    @abstractmethod
    def create_action_file(self, item) -> Path:
        """Write a .md trigger file to /Needs_Action/. Return the file path."""
        pass

    # ── Provided helpers ──────────────────────────────────────────────────────

    def write_audit_log(self, action_type: str, target: str, result: str, **kwargs):
        """Append a JSON audit entry to /Logs/YYYY-MM-DD.json (Section 6.3 format)."""
        date = datetime.now().strftime("%Y-%m-%d")
        log_file = self.logs_dir / f"{date}.json"

        entry = {
            "timestamp": datetime.now().isoformat(),
            "action_type": action_type,
            "actor": self.__class__.__name__,
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

    def _check_with_retry(self) -> list:
        """Call check_for_updates() with exponential backoff retry."""
        for attempt in range(self.max_retries):
            try:
                return self.check_for_updates()
            except Exception as e:
                if attempt == self.max_retries - 1:
                    self.logger.error(f"All {self.max_retries} attempts failed: {e}")
                    self.write_audit_log(
                        action_type="check_failed",
                        target="external_source",
                        result="error",
                        error=str(e),
                        attempts=self.max_retries,
                    )
                    return []
                delay = min(self.retry_base_delay * (2 ** attempt), 60)
                self.logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                time.sleep(delay)
        return []

    def stop(self):
        """Gracefully stop the run loop."""
        self._running = False
        self.logger.info(f"{self.__class__.__name__} stopping...")

    # ── Main run loop ─────────────────────────────────────────────────────────

    def run(self):
        """
        Main watcher loop (Section 2A pattern):
          1. check_for_updates()
          2. create_action_file() for each new item
          3. sleep check_interval seconds
          4. repeat forever
        """
        self._running = True
        self.logger.info(f"Starting {self.__class__.__name__}")
        self.logger.info(f"Vault: {self.vault_path}")
        self.logger.info(f"Check interval: {self.check_interval}s")

        while self._running:
            try:
                items = self._check_with_retry()
                new_count = 0

                for item in items:
                    try:
                        filepath = self.create_action_file(item)
                        self.logger.info(f"Action file created: {filepath.name}")
                        self.write_audit_log(
                            action_type="action_file_created",
                            target=str(filepath.name),
                            result="success",
                        )
                        new_count += 1
                    except Exception as e:
                        self.logger.error(f"Failed to create action file for {item}: {e}")
                        self.write_audit_log(
                            action_type="action_file_failed",
                            target=str(item),
                            result="error",
                            error=str(e),
                        )

                if new_count > 0:
                    self.logger.info(f"Processed {new_count} new item(s)")
                else:
                    self.logger.info("No new items.")

            except KeyboardInterrupt:
                self.logger.info("Keyboard interrupt received.")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error in run loop: {e}")

            self.logger.info(f"Sleeping {self.check_interval}s...")
            time.sleep(self.check_interval)

        self.logger.info(f"{self.__class__.__name__} stopped.")
