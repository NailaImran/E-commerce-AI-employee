#!/usr/bin/env python3
"""
Get a fresh Facebook Page Access Token via browser automation.
Browser opens on screen — log in to Facebook, then generate token in Graph API Explorer.
"""

from playwright.sync_api import sync_playwright
from pathlib import Path
from urllib.request import urlopen
import time, json, ctypes, threading

PROFILE_DIR = str(Path("E:/AI_Employee_Vault/.secrets/facebook_profile"))
VAULT = Path("E:/AI_Employee_Vault")


def dialog_wait_with_page(page, title, msg):
    """Show Windows dialog in background thread; keep Playwright alive until user clicks OK."""
    done = threading.Event()
    threading.Thread(
        target=lambda: [ctypes.windll.user32.MessageBoxW(0, msg, title, 0x40), done.set()],
        daemon=True
    ).start()
    while not done.is_set():
        try:
            page.wait_for_timeout(1000)
        except Exception:
            break


def load_env():
    env = {}
    for line in open(VAULT / ".env", encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    return env


def update_env(key, value):
    lines = []
    for line in open(VAULT / ".env", encoding="utf-8"):
        if line.strip().startswith(f"{key}="):
            lines.append(f"{key}={value}\n")
        else:
            lines.append(line)
    with open(VAULT / ".env", "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"[OK] .env updated: {key}={value[:30]}...")


def extract_token_from_page(page):
    try:
        return page.evaluate("""
            () => {
                const inputs = document.querySelectorAll('input, textarea');
                for (const el of inputs) {
                    if (el.value && el.value.startsWith('EAA') && el.value.length > 50)
                        return el.value;
                }
                const text = document.body.innerText || '';
                const m = text.match(/EAA[A-Za-z0-9]{50,}/);
                return m ? m[0] : null;
            }
        """)
    except Exception:
        return None


def get_page_info(token, page_id):
    url = f"https://graph.facebook.com/v21.0/{page_id}?fields=name,fan_count&access_token={token}"
    try:
        resp = json.loads(urlopen(url, timeout=10).read())
        return resp
    except Exception as e:
        return {"error": str(e)}


def main():
    env = load_env()
    page_id = env.get("META_PAGE_ID", "")
    Path(PROFILE_DIR).mkdir(parents=True, exist_ok=True)
    Path(VAULT / "Logs").mkdir(exist_ok=True)

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            slow_mo=80,
            viewport={"width": 1300, "height": 900},
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        # ── STEP 1: Facebook Login ──────────────────────────────────────────
        print("\n[STEP 1] Opening Facebook...")
        page.goto("https://www.facebook.com/")
        page.wait_for_timeout(4000)

        dialog_wait_with_page(
            page,
            "AI Employee — Step 1: Log in to Facebook",
            "The browser is open on Facebook.\n\n"
            "1. Log in with your email + password\n"
            "2. Complete 2FA if asked\n"
            "3. Wait until you see your Facebook home feed\n\n"
            "Then click OK to continue."
        )

        page.wait_for_timeout(2000)
        ss = str(VAULT / "Logs" / "fb_logged_in.png")
        page.screenshot(path=ss)
        print(f"[*] Screenshot saved: {ss}")

        # ── STEP 2: Graph API Explorer → Generate Token ────────────────────
        print("\n[STEP 2] Opening Meta Graph API Explorer...")
        page.goto("https://developers.facebook.com/tools/explorer/")
        page.wait_for_timeout(6000)

        ss2 = str(VAULT / "Logs" / "meta_explorer.png")
        page.screenshot(path=ss2)
        print(f"[*] Screenshot saved: {ss2}")

        dialog_wait_with_page(
            page,
            "AI Employee — Step 2: Generate Access Token",
            "Meta Graph API Explorer is open.\n\n"
            "1. Select your App from the top dropdown\n"
            "   (App ID: 26179122101776440)\n"
            "2. Click 'Generate Access Token'\n"
            "3. Add these permissions:\n"
            "   - pages_show_list\n"
            "   - pages_manage_posts\n"
            "   - instagram_basic\n"
            "   - instagram_content_publish\n"
            "4. Approve the dialog\n\n"
            "Click OK AFTER the token appears."
        )

        page.wait_for_timeout(2000)

        # Try to auto-read token
        token = extract_token_from_page(page)

        ss3 = str(VAULT / "Logs" / "meta_explorer_token.png")
        page.screenshot(path=ss3)
        print(f"[*] Screenshot saved: {ss3}")

        if token:
            print(f"\n[OK] Token auto-detected: {token[:30]}...")
            info = get_page_info(token, page_id)
            print(f"[API] Page info: {json.dumps(info, indent=2)}")

            if "error" not in info:
                update_env("META_PAGE_ACCESS_TOKEN", token)
                ctypes.windll.user32.MessageBoxW(
                    0,
                    f"Facebook connected!\n\nPage: {info.get('name','')}\n"
                    f"Token saved to .env\n\nAll done!",
                    "AI Employee — Facebook Connected",
                    0x40
                )
            else:
                print(f"[!] API error: {info}")
                ctypes.windll.user32.MessageBoxW(
                    0,
                    f"Token found but API check failed:\n{info.get('error','')}\n\n"
                    "Token was saved anyway — check .env",
                    "AI Employee — Warning",
                    0x30
                )
                update_env("META_PAGE_ACCESS_TOKEN", token)
        else:
            print("[!] Could not auto-read token from page.")
            ctypes.windll.user32.MessageBoxW(
                0,
                "Could not read the token automatically.\n\n"
                "Please copy the token from the Graph API Explorer\n"
                "and paste it manually into META_PAGE_ACCESS_TOKEN in your .env file.",
                "AI Employee — Manual Step Needed",
                0x30
            )

        ctx.close()
        print("\n[DONE]")


if __name__ == "__main__":
    main()
