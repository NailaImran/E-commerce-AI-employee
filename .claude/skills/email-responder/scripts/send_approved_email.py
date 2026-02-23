#!/usr/bin/env python3
"""
Send Approved Email — E-commerce AI Employee (Silver Tier)

Reads an approved EMAIL_REPLY_*.md from /Approved/ and sends it via Gmail API.
Called by the approval_watcher.py when a file moves to /Approved/.

Usage:
    python send_approved_email.py --file E:/AI_Employee_Vault/Approved/EMAIL_REPLY_2026-02-21_10-30.md --vault E:/AI_Employee_Vault
    python send_approved_email.py --file ... --vault ... --dry-run

Requirements:
    pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
"""

import argparse
import base64
import json
import logging
import re
import sys
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("EmailSender")

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def get_gmail_send_service(vault: Path):
    """Authenticate Gmail with send scope."""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        logger.error("Run: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
        sys.exit(1)

    secrets_dir = vault / ".secrets"
    token_path = secrets_dir / "gmail_send_token.json"
    credentials_path = secrets_dir / "credentials.json"

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def parse_approval_file(filepath: Path) -> dict:
    """Parse frontmatter and body from an approval .md file."""
    text = filepath.read_text(encoding="utf-8")

    # Extract frontmatter
    fm_match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    frontmatter = {}
    if fm_match:
        for line in fm_match.group(1).split("\n"):
            if ": " in line:
                k, v = line.split(": ", 1)
                frontmatter[k.strip()] = v.strip()

    # Extract reply body (between "## Drafted Reply" and next "---")
    body_match = re.search(r"## Drafted Reply\n\n(.*?)\n\n---", text, re.DOTALL)
    body = body_match.group(1).strip() if body_match else ""

    return {
        "to": frontmatter.get("to", ""),
        "subject": frontmatter.get("subject", "Re: Your Message"),
        "body": body,
        "type": frontmatter.get("type", ""),
        "expires": frontmatter.get("expires", ""),
    }


def log_action(vault: Path, action: dict):
    """Append to audit log."""
    logs_dir = vault / "Logs"
    logs_dir.mkdir(exist_ok=True)
    log_file = logs_dir / f"{datetime.now().strftime('%Y-%m-%d')}.json"

    entries = []
    if log_file.exists():
        try:
            entries = json.loads(log_file.read_text())
        except Exception:
            pass

    entries.append(action)
    log_file.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def send_email(vault: Path, approval_file: Path, dry_run: bool = False):
    parsed = parse_approval_file(approval_file)

    if not parsed["to"]:
        logger.error(f"No recipient in approval file: {approval_file.name}")
        return False

    if not parsed["body"]:
        logger.error(f"No email body found in: {approval_file.name}")
        return False

    logger.info(f"Sending email to: {parsed['to']} | Subject: {parsed['subject']}")

    if dry_run:
        logger.info(f"[DRY RUN] Would send:\nTo: {parsed['to']}\nSubject: {parsed['subject']}\n\n{parsed['body']}")
        return True

    try:
        service = get_gmail_send_service(vault)
        message = MIMEText(parsed["body"])
        message["to"] = parsed["to"]
        message["subject"] = parsed["subject"]
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        service.users().messages().send(
            userId="me",
            body={"raw": raw}
        ).execute()

        logger.info("Email sent successfully.")

        # Move file to Done
        done_dir = vault / "Done"
        done_dir.mkdir(exist_ok=True)
        approval_file.rename(done_dir / approval_file.name)
        logger.info(f"Moved {approval_file.name} to /Done/")

        # Audit log
        log_action(vault, {
            "timestamp": datetime.now().isoformat(),
            "action_type": "email_send",
            "actor": "claude_code",
            "target": parsed["to"],
            "parameters": {"subject": parsed["subject"]},
            "approval_status": "approved",
            "approved_by": "human",
            "result": "success",
        })
        return True

    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        log_action(vault, {
            "timestamp": datetime.now().isoformat(),
            "action_type": "email_send",
            "actor": "claude_code",
            "target": parsed["to"],
            "result": "error",
            "error": str(e),
        })
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to approved EMAIL_REPLY_*.md file")
    parser.add_argument("--vault", default="E:/AI_Employee_Vault")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    send_email(Path(args.vault), Path(args.file), args.dry_run)


if __name__ == "__main__":
    main()
