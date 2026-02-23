#!/usr/bin/env python3
"""
LinkedIn OAuth2 Token Fetcher — One-time setup

Opens a browser for LinkedIn authorization, receives the callback,
exchanges the code for an access token, and saves it to .secrets/linkedin_token.txt

Usage:
    python get_linkedin_token.py
"""

import json
import secrets
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests

SECRETS_DIR = Path("E:/AI_Employee_Vault/.secrets")
CREDS_FILE = SECRETS_DIR / "linkedin_creds.json"
TOKEN_FILE = SECRETS_DIR / "linkedin_token.txt"

REDIRECT_URI = "http://localhost:8080"
SCOPES = "openid profile w_member_social"
AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"


def load_creds():
    with open(CREDS_FILE) as f:
        return json.load(f)


received_code = None
received_state = None


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global received_code, received_state
        params = parse_qs(urlparse(self.path).query)
        received_code = params.get("code", [None])[0]
        received_state = params.get("state", [None])[0]

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"""
        <html><body style='font-family:sans-serif;text-align:center;padding:50px'>
        <h2>Authorization successful!</h2>
        <p>You can close this window and return to the terminal.</p>
        </body></html>
        """)

    def log_message(self, format, *args):
        pass  # Suppress server logs


def main():
    creds = load_creds()
    client_id = creds["client_id"]
    client_secret = creds["client_secret"]
    state = secrets.token_urlsafe(16)

    # Build auth URL
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "state": state,
        "scope": SCOPES,
    }
    auth_url = f"{AUTH_URL}?{urlencode(params)}"

    print("=" * 60)
    print("LinkedIn OAuth2 Authorization")
    print("=" * 60)
    print()
    print("Opening browser for LinkedIn login...")
    print(f"If it doesn't open, visit:\n{auth_url}")
    print()
    webbrowser.open(auth_url)

    # Start local server to catch redirect
    print("Waiting for LinkedIn callback on http://localhost:8080 ...")
    server = HTTPServer(("localhost", 8080), CallbackHandler)
    server.handle_request()

    if not received_code:
        print("[ERROR] No authorization code received.")
        raise SystemExit(1)

    if received_state != state:
        print("[ERROR] State mismatch — possible CSRF attack.")
        raise SystemExit(1)

    # Exchange code for token
    print("Exchanging authorization code for access token...")
    resp = requests.post(TOKEN_URL, data={
        "grant_type": "authorization_code",
        "code": received_code,
        "redirect_uri": REDIRECT_URI,
        "client_id": client_id,
        "client_secret": client_secret,
    }, timeout=15)

    if resp.status_code != 200:
        print(f"[ERROR] Token exchange failed: {resp.status_code}")
        print(resp.text)
        raise SystemExit(1)

    token_data = resp.json()
    access_token = token_data.get("access_token")
    expires_in = token_data.get("expires_in", "unknown")

    if not access_token:
        print(f"[ERROR] No access_token in response: {token_data}")
        raise SystemExit(1)

    TOKEN_FILE.write_text(access_token)
    print()
    print(f"[OK] Access token saved to: {TOKEN_FILE}")
    print(f"[OK] Token expires in: {int(expires_in)//86400} days")
    print()
    print("LinkedIn is ready. You can now use the linkedin-poster skill.")


if __name__ == "__main__":
    main()
