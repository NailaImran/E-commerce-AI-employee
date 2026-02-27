#!/usr/bin/env python3
"""Post a tweet via Playwright. First run: log in manually. Subsequent runs: auto."""

from playwright.sync_api import sync_playwright
from pathlib import Path
import time, datetime

TWEET = """Your Shopify store doesn't sleep. Neither does your AI employee.

Emails answered. Orders flagged. Content posted. 24/7.

Built with Claude Code. #ecommerce #shopify"""

PROFILE_DIR = str(Path("E:/AI_Employee_Vault/.secrets/browser_profile"))
VAULT = Path("E:/AI_Employee_Vault")

def post_tweet():
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            slow_mo=150,
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        page.goto("https://x.com/login")
        page.wait_for_timeout(3000)

        if "login" in page.url or "i/flow" in page.url:
            import subprocess
            subprocess.Popen([
                "powershell", "-Command",
                "[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null; "
                "[System.Windows.Forms.MessageBox]::Show('Twitter/X login window is open! Log in now then close this dialog.', 'AI Employee — Twitter Login', 'OK', 'Information')"
            ])
            print()
            print("=" * 60)
            print("  BROWSER IS OPEN — LOG IN TO TWITTER NOW")
            print("  A popup notification was sent to your desktop.")
            print("  Waiting up to 5 minutes...")
            print("=" * 60)
            for i in range(60):
                time.sleep(5)
                cur = page.url
                remaining = (59 - i) * 5
                if "login" not in cur and "i/flow" not in cur:
                    print(f"\n[*] Login detected! URL: {cur}")
                    break
                print(f"  {remaining}s remaining... (current: {cur[:60]})")
            else:
                print("[!] Login timed out. Run again after logging in.")
                ctx.close()
                return

        page.wait_for_timeout(2000)
        print("[*] Navigating to compose...")
        page.goto("https://x.com/compose/post")
        page.wait_for_timeout(2000)

        print("[*] Waiting for tweet box...")
        page.wait_for_selector('[data-testid="tweetTextarea_0"]', timeout=15000)
        page.click('[data-testid="tweetTextarea_0"]')
        page.wait_for_timeout(500)

        print(f"[*] Typing tweet ({len(TWEET)} chars)...")
        page.keyboard.type(TWEET, delay=30)
        page.wait_for_timeout(1500)

        print("[*] Waiting for Post button to enable...")
        # Try both possible test IDs for the Post button
        post_btn = None
        for selector in ['[data-testid="tweetButtonInline"]', '[data-testid="tweetButton"]']:
            try:
                page.wait_for_selector(f'{selector}:not([disabled])', timeout=10000)
                post_btn = selector
                break
            except Exception:
                pass
        if not post_btn:
            # Fallback: use JS to find and click any enabled Post button
            print("[*] Trying JS fallback to find Post button...")
            page.evaluate("""
                () => {
                    const btns = [...document.querySelectorAll('button[data-testid]')];
                    const post = btns.find(b => !b.disabled && (b.dataset.testid.includes('tweet') || b.innerText.trim() === 'Post'));
                    if (post) post.click();
                }
            """)
        else:
            page.click(post_btn)
        page.wait_for_timeout(4000)

        if "compose" not in page.url:
            print("[OK] Tweet posted! Session saved for future runs.")
            log_file = VAULT / "Logs" / "twitter_posts.md"
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"\n## {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n**Method**: Browser automation (Playwright)\n\n{TWEET}\n\n---")
        else:
            print("[!] Compose page still visible — check browser window.")
            time.sleep(10)

        ctx.close()

if __name__ == "__main__":
    post_tweet()
