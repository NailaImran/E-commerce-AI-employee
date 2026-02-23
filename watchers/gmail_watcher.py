#!/usr/bin/env python3
"""
GmailWatcher — monitors Gmail for unread customer emails.
Inherits from BaseWatcher (Section 2A pattern).

Saves each email as EMAIL_*.md in /Needs_Action/ for the email-responder skill.

Usage:
    python gmail_watcher.py
    python gmail_watcher.py --vault E:/AI_Employee_Vault --dry-run
"""

import argparse
import base64
import sys
from datetime import datetime
from pathlib import Path

# Allow running from any directory
sys.path.insert(0, str(Path(__file__).parent))
from base_watcher import BaseWatcher

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


class GmailWatcher(BaseWatcher):

    def __init__(self, vault_path: str, credentials_path: str, dry_run: bool = False):
        super().__init__(vault_path=vault_path, check_interval=120)
        self.credentials_path = Path(credentials_path)
        self.token_path = self.vault_path / ".secrets" / "gmail_token.json"
        self.processed_log = self.logs_dir / "gmail_processed_ids.json"
        self.dry_run = dry_run
        self.processed_ids: set = self._load_processed_ids()
        self.service = self._authenticate()

    def _load_processed_ids(self) -> set:
        if self.processed_log.exists():
            try:
                import json
                ids = set(json.loads(self.processed_log.read_text()))
                self.logger.info(f"Loaded {len(ids)} previously processed IDs")
                return ids
            except Exception:
                pass
        return set()

    def _save_processed_ids(self):
        import json
        self.processed_log.write_text(
            json.dumps(list(self.processed_ids)), encoding="utf-8"
        )

    def _authenticate(self):
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError:
            self.logger.error("Run: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
            sys.exit(1)

        creds = None
        if self.token_path.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not self.credentials_path.exists():
                    self.logger.error(f"credentials.json not found at {self.credentials_path}")
                    sys.exit(1)
                flow = InstalledAppFlow.from_client_secrets_file(str(self.credentials_path), SCOPES)
                creds = flow.run_local_server(port=8080, open_browser=True)
            self.token_path.write_text(creds.to_json())
            self.logger.info(f"Token saved to {self.token_path}")

        self.logger.info("Gmail authenticated successfully")
        return build("gmail", "v1", credentials=creds)

    def check_for_updates(self) -> list:
        """Poll Gmail for unread primary emails not yet processed."""
        result = self.service.users().messages().list(
            userId="me",
            q="is:unread category:primary",
            maxResults=20,
        ).execute()
        messages = result.get("messages", [])
        return [m for m in messages if m["id"] not in self.processed_ids]

    def create_action_file(self, item) -> Path:
        """Fetch full message and write EMAIL_*.md to /Needs_Action/."""
        msg = self.service.users().messages().get(
            userId="me", id=item["id"], format="full"
        ).execute()

        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        sender = headers.get("From", "Unknown")
        subject = headers.get("Subject", "No Subject")
        date = headers.get("Date", datetime.now().isoformat())
        body = self._extract_body(msg)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"EMAIL_{timestamp}_{item['id'][:8]}.md"
        filepath = self.needs_action / filename

        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would save: From={sender} Subject={subject}")
            self.processed_ids.add(item["id"])
            self._save_processed_ids()
            return filepath

        content = f"""---
type: customer_email
gmail_message_id: {item['id']}
from: {sender}
subject: {subject}
received: {date}
processed: {datetime.now().isoformat()}
status: pending
classification: unclassified
---

## Email Content

**From**: {sender}
**Subject**: {subject}
**Date**: {date}

---

{body[:2000]}

---

## Instructions for Claude

Use the `email-responder` skill to:
1. Classify this email (order_query / complaint / refund_request / shipping_query / general)
2. Draft a professional reply
3. Write approval file to `/Pending_Approval/EMAIL_REPLY_*.md`
4. Move this file to `/Done/` after drafting
"""
        filepath.write_text(content, encoding="utf-8")
        self.processed_ids.add(item["id"])
        self._save_processed_ids()
        return filepath

    def _extract_body(self, msg: dict) -> str:
        payload = msg.get("payload", {})

        def decode_part(part):
            data = part.get("body", {}).get("data", "")
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore") if data else ""

        if payload.get("mimeType") == "text/plain":
            return decode_part(payload)
        for part in payload.get("parts", []):
            if part.get("mimeType") == "text/plain":
                return decode_part(part)
            for subpart in part.get("parts", []):
                if subpart.get("mimeType") == "text/plain":
                    return decode_part(subpart)
        return msg.get("snippet", "")


def main():
    parser = argparse.ArgumentParser(description="Gmail Watcher — E-commerce AI Employee")
    parser.add_argument("--vault", default="E:/AI_Employee_Vault")
    parser.add_argument("--credentials", default="E:/AI_Employee_Vault/.secrets/credentials.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    GmailWatcher(
        vault_path=args.vault,
        credentials_path=args.credentials,
        dry_run=args.dry_run,
    ).run()


if __name__ == "__main__":
    main()
