#!/usr/bin/env python3
"""
Gmail OAuth Setup — Run this ONCE from your terminal to authorize Gmail access.
It will open a browser, you sign in, and the token is saved automatically.

Usage:
    python setup_gmail_auth.py

Requirements:
    pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
"""
import sys
from pathlib import Path

CREDENTIALS = Path("E:/AI_Employee_Vault/.secrets/credentials.json")
TOKEN = Path("E:/AI_Employee_Vault/.secrets/gmail_token.json")
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


def main():
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("ERROR: Missing library. Run:")
        print("  pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
        sys.exit(1)

    if not CREDENTIALS.exists():
        print(f"ERROR: credentials.json not found at {CREDENTIALS}")
        sys.exit(1)

    print("=" * 60)
    print("Gmail OAuth Setup")
    print("=" * 60)
    print(f"Credentials: {CREDENTIALS}")
    print(f"Token will be saved to: {TOKEN}")
    print()
    print("A browser window will open. Sign in with your Google account")
    print("and click Allow to grant Gmail access.")
    print()

    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS), SCOPES)
    creds = flow.run_local_server(port=8080, open_browser=True)

    TOKEN.parent.mkdir(exist_ok=True)
    TOKEN.write_text(creds.to_json())

    print()
    print("=" * 60)
    print(f"SUCCESS! Token saved to: {TOKEN}")
    print("You can now run gmail_watcher.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
