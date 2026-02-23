#!/usr/bin/env python3
"""
Windows Task Scheduler Setup — E-commerce AI Employee (Silver Tier)

Registers a daily 8 PM task to run daily_summary.py.

Run once as Administrator:
    python setup_scheduler.py

To remove the task:
    python setup_scheduler.py --remove
"""

import argparse
import subprocess
import sys
from pathlib import Path

TASK_NAME = "EcommerceAIEmployee_DailySummary"
SCRIPT_PATH = Path("E:/E-commerce-employee/watchers/daily_summary.py")
VAULT_PATH = "E:/AI_Employee_Vault"
PYTHON_EXE = sys.executable
TRIGGER_TIME = "20:00"  # 8 PM


def register_task():
    """Create a daily scheduled task using schtasks."""
    cmd = [
        "schtasks", "/create",
        "/tn", TASK_NAME,
        "/tr", f'"{PYTHON_EXE}" "{SCRIPT_PATH}" --vault "{VAULT_PATH}"',
        "/sc", "DAILY",
        "/st", TRIGGER_TIME,
        "/f",  # Force overwrite if exists
        "/ru", "SYSTEM",  # Run as SYSTEM (no login required)
    ]

    print(f"Registering task: {TASK_NAME}")
    print(f"Script: {SCRIPT_PATH}")
    print(f"Schedule: Daily at {TRIGGER_TIME}")
    print()

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print(f"[OK] Task registered: {TASK_NAME}")
        print(f"[OK] Daily summary will run every day at 8:00 PM")
        print()
        print("To verify:")
        print(f'  schtasks /query /tn "{TASK_NAME}"')
        print()
        print("To run now (test):")
        print(f'  schtasks /run /tn "{TASK_NAME}"')
    else:
        print(f"[ERROR] Failed to register task:")
        print(result.stderr)
        print()
        print("Try running this script as Administrator.")
        sys.exit(1)


def remove_task():
    """Delete the scheduled task."""
    result = subprocess.run(
        ["schtasks", "/delete", "/tn", TASK_NAME, "/f"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"[OK] Task removed: {TASK_NAME}")
    else:
        print(f"[ERROR] {result.stderr}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--remove", action="store_true", help="Remove the scheduled task")
    args = parser.parse_args()

    if args.remove:
        remove_task()
    else:
        register_task()


if __name__ == "__main__":
    main()
