#!/usr/bin/env python3
"""
Connect Instagram to Facebook Page and refresh the Page Access Token.
Browser opens on screen — follow Windows dialogs to complete each step.
"""

from playwright.sync_api import sync_playwright
from pathlib import Path
from urllib.request import urlopen
import time, json, os, ctypes

PROFILE_DIR = str(Path("E:/AI_Employee_Vault/.secrets/facebook_profile"))
VAULT = Path("E:/AI_Employee_Vault")


import ctypes
import threading

def dialog(title, msg):
    """Show a Windows popup without blocking (fire-and-forget)."""
    threading.Thread(
        target=lambda: ctypes.windll.user32.MessageBoxW(0, msg, title, 0x40),
        daemon=True
    ).start()


def dialog_wait_with_page(page, title, msg):
    """Show dialog in background thread; keep Playwright event loop alive until user clicks OK."""
    done = threading.Event()
    threading.Thread(
        target=lambda: [ctypes.windll.user32.MessageBoxW(0, msg, title, 0x40), done.set()],
        daemon=True
    ).start()
    # Keep browser heartbeat while waiting for user
    while not done.is_set():
        try:
            page.wait_for_timeout(1000)
        except Exception:
            break  # Browser closed


# Alias for backwards compat
def dialog_wait(title, msg):
    ctypes.windll.user32.MessageBoxW(0, msg, title, 0x40)


def load_env():
    env = {}
    for line in open(VAULT / ".env", encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    return env


def update_env(updates: dict):
    lines = []
    for line in open(VAULT / ".env", encoding="utf-8"):
        stripped = line.strip()
        updated = False
        for key, val in updates.items():
            if stripped.startswith(f"{key}="):
                lines.append(f"{key}={val}\n")
                updated = True
                break
        if not updated:
            lines.append(line)
    with open(VAULT / ".env", "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"[OK] .env updated: {list(updates.keys())}")


def is_logged_in_facebook(page):
    """Check if actually logged into Facebook by looking for nav elements."""
    try:
        # If we see the main nav or a profile link, we're logged in
        logged_in = page.evaluate("""
            () => {
                // Check for Facebook nav bar (logged-in indicator)
                const nav = document.querySelector('[aria-label="Facebook"], [role="navigation"]');
                const feed = document.querySelector('[role="feed"]');
                const home = document.querySelector('a[href="/"][aria-label="Home"]');
                return !!(nav || feed || home);
            }
        """)
        return logged_in
    except Exception:
        return False


def wait_for_facebook_login(page):
    """Open Facebook and wait for user to confirm they are logged in."""
    page.goto("https://www.facebook.com/")
    page.wait_for_timeout(4000)

    cur = page.url
    # If already logged in (URL would redirect to /home or show feed)
    if "/home" in cur or "feed" in cur:
        print("[*] Already logged in to Facebook!")
        return True

    # Show blocking dialog — script waits here until user clicks OK
    dialog_wait_with_page(
        page,
        "AI Employee — Log in to Facebook",
        "A browser window is open.\n\n"
        "Steps:\n"
        "1. Find the Chromium browser window on your taskbar\n"
        "2. Log in with your Facebook email + password\n"
        "3. Enter 2FA code if asked\n"
        "4. Wait until you see the Facebook home feed\n\n"
        "Then click OK here to continue."
    )

    print("[*] User confirmed Facebook login. Proceeding...")
    return True


def get_instagram_id_from_api(token, page_id):
    url = f"https://graph.facebook.com/v21.0/{page_id}?fields=name,instagram_business_account&access_token={token}"
    try:
        resp = json.loads(urlopen(url, timeout=10).read())
        print("[API Response]:", json.dumps(resp, indent=2))
        ig = resp.get("instagram_business_account", {})
        return ig.get("id")
    except Exception as e:
        print(f"[!] API error: {e}")
        return None


def extract_token_from_page(page):
    """Try to extract a token starting with EAA from any input on the page."""
    try:
        token = page.evaluate("""
            () => {
                const all = document.body.innerText || '';
                const match = all.match(/EAA[A-Za-z0-9+/]{50,}/);
                if (match) return match[0];
                const inputs = document.querySelectorAll('input, textarea');
                for (const el of inputs) {
                    const v = el.value || '';
                    if (v.startsWith('EAA') && v.length > 50) return v;
                }
                return null;
            }
        """)
        return token
    except Exception:
        return None


def main():
    env = load_env()
    Path(PROFILE_DIR).mkdir(parents=True, exist_ok=True)
    Path(VAULT / "Logs").mkdir(exist_ok=True)
    Path(VAULT / ".secrets").mkdir(exist_ok=True)

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            slow_mo=80,
            viewport={"width": 1300, "height": 900},
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        # ── STEP 1: Log in to Facebook ─────────────────────────────────────────
        print("\n[STEP 1] Opening Facebook...")
        if not wait_for_facebook_login(page):
            print("[!] Could not log in to Facebook. Exiting.")
            ctx.close()
            return

        page.wait_for_timeout(2000)
        ss1 = str(VAULT / "Logs" / "fb_logged_in.png")
        page.screenshot(path=ss1)
        print(f"[*] Facebook logged in. Screenshot: {ss1}")

        # ── STEP 2: Open Instagram Settings via Business Suite ─────────────────
        print("\n[STEP 2] Opening Instagram account settings in Business Suite...")
        page.goto("https://business.facebook.com/settings/instagram-accounts/")
        page.wait_for_timeout(5000)

        ss2 = str(VAULT / "Logs" / "fb_instagram_settings.png")
        page.screenshot(path=ss2)
        print(f"[*] Screenshot: {ss2}")

        dialog_wait_with_page(
            page,
            "AI Employee — Connect Instagram (Step 2)",
            "Business Suite > Instagram Accounts is open.\n\n"
            "Steps to connect:\n"
            "1. Click 'Add' or 'Connect' next to Instagram\n"
            "2. Log in with your Instagram username/password\n"
            "3. Select 'Business Account' if prompted\n"
            "4. Confirm the connection\n\n"
            "Click OK here AFTER Instagram is connected."
        )

        # Screenshot after connection
        page.wait_for_timeout(2000)
        ss2b = str(VAULT / "Logs" / "fb_instagram_after.png")
        page.screenshot(path=ss2b)
        print(f"[*] After-connect screenshot: {ss2b}")

        # ── STEP 3: Get fresh token from Graph API Explorer ───────────────────
        print("\n[STEP 3] Opening Meta Graph API Explorer...")
        page.goto("https://developers.facebook.com/tools/explorer/")
        page.wait_for_timeout(6000)

        ss3 = str(VAULT / "Logs" / "meta_explorer.png")
        page.screenshot(path=ss3)
        print(f"[*] Screenshot: {ss3}")

        dialog_wait_with_page(
            page,
            "AI Employee — Generate Token (Step 3)",
            "Meta Graph API Explorer is open.\n\n"
            "Steps:\n"
            "1. Select your App from the top dropdown\n"
            "2. Click 'Generate Access Token'\n"
            "3. Add permissions:\n"
            "   - pages_show_list\n"
            "   - pages_manage_posts\n"
            "   - instagram_basic\n"
            "   - instagram_content_publish\n"
            "4. Approve the dialog\n\n"
            "Click OK here AFTER the token appears in the input box."
        )

        # Try to auto-read token
        page.wait_for_timeout(2000)
        token = extract_token_from_page(page)

        if token:
            print(f"[*] Token auto-detected! {token[:25]}...")
        else:
            print("[!] Could not auto-read token. Checking screenshots...")
            ss3b = str(VAULT / "Logs" / "meta_explorer_token.png")
            page.screenshot(path=ss3b)

        # ── STEP 4: Check Instagram ID ─────────────────────────────────────────
        page_id = env.get("META_PAGE_ID", "")
        instagram_id = None

        if token:
            print(f"\n[STEP 4] Fetching Instagram ID for Page {page_id}...")
            instagram_id = get_instagram_id_from_api(token, page_id)

        if instagram_id:
            update_env({
                "META_PAGE_ACCESS_TOKEN": token,
                "META_INSTAGRAM_ACCOUNT_ID": instagram_id,
            })
            print(f"\n[OK] Instagram Business Account ID: {instagram_id}")
            dialog("AI Employee — Success!",
                   f"Everything connected!\n\n"
                   f"Instagram Business Account ID:\n{instagram_id}\n\n"
                   f".env updated. You can now post to\n"
                   f"Facebook and Instagram automatically!")
        elif token:
            update_env({"META_PAGE_ACCESS_TOKEN": token})
            dialog("AI Employee",
                   "Token saved.\n\n"
                   "Instagram ID not found yet — make sure Instagram\n"
                   "was connected in Step 2, then run this script again.")
        else:
            dialog("AI Employee",
                   "Token could not be auto-read.\n\n"
                   "Please copy the token shown in the Graph API Explorer\n"
                   "and run the script again, OR paste it into\n"
                   "META_PAGE_ACCESS_TOKEN in your .env file.")

        ctx.close()
        print("\n[DONE]")


if __name__ == "__main__":
    main()
