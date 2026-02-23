#!/usr/bin/env python3
"""
LinkedIn OAuth Callback Server
Listens on localhost:8080, catches the auth code, exchanges for token, saves it.
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import requests

SECRETS = Path("E:/AI_Employee_Vault/.secrets")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        params = parse_qs(urlparse(self.path).query)
        code = params.get("code", [None])[0]
        state = params.get("state", [None])[0]

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        if not code:
            error = params.get("error", [None])[0]
            error_desc = params.get("error_description", ["No details"])[0]
            msg = f"<h2>Error: no code received.</h2><p><b>{error}</b>: {error_desc}</p><p>Full path: <code>{self.path}</code></p>"
            self.wfile.write(msg.encode())
            print(f"[ERROR] LinkedIn returned: {error} - {error_desc}")
            print(f"[DEBUG] Full path: {self.path}")
            self.server._done = True
            return

        # Verify state
        saved_state = (SECRETS / "linkedin_state.txt").read_text().strip()
        if state != saved_state:
            self.wfile.write(b"<h2>Error: state mismatch.</h2>")
            return

        # Exchange code for token
        creds = json.loads((SECRETS / "linkedin_creds.json").read_text())
        resp = requests.post("https://www.linkedin.com/oauth/v2/accessToken", data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "http://localhost:8080",
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
        }, timeout=15)

        if resp.status_code == 200:
            token = resp.json().get("access_token", "")
            expires = resp.json().get("expires_in", 0)
            (SECRETS / "linkedin_token.txt").write_text(token)
            days = expires // 86400
            msg = f"<h2>LinkedIn connected!</h2><p>Token saved. Expires in {days} days.</p><p>You can close this window.</p>"
            self.wfile.write(msg.encode())
            print(f"\n[OK] Token saved to {SECRETS / 'linkedin_token.txt'}")
            print(f"[OK] Expires in {days} days")
        else:
            self.wfile.write(f"<h2>Error {resp.status_code}</h2><pre>{resp.text}</pre>".encode())
            print(f"[ERROR] Token exchange failed: {resp.status_code} {resp.text}")

        # Signal server to stop
        self.server._done = True

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print("[READY] Callback server listening on http://localhost:8080")
    print("[READY] Waiting for LinkedIn redirect...")
    sys.stdout.flush()
    server = HTTPServer(("localhost", 8080), Handler)
    server._done = False
    while not server._done:
        server.handle_request()
    print("[DONE] Server stopped.")
