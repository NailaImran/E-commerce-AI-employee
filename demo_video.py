#!/usr/bin/env python3
"""
AI Employee — Video Demo Script
Runs a full recorded walkthrough of all capabilities.

Usage:
    python demo_video.py

HOW TO RECORD:
    1. Press Win+G  → Xbox Game Bar → click Record (or Win+Alt+R)
       OR open OBS and start recording
    2. Run this script — it opens a maximized browser
    3. Watch it walk through everything automatically
    4. Stop recording when browser closes

The script will:
    Slide 1  — Intro / title card
    Slide 2  — Capabilities overview
    Slide 3  — System architecture
    Slide 4  — HITL workflow
    Slide 5  — Tech stack
    GitHub   — Live repo
    Logs     — Real JSON audit log
    Odoo     — Live sale orders + invoice
    LinkedIn — Published hackathon post
    Instagram— Business account post
    Slide 6  — Gold Tier badge / outro
"""

import time
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

VAULT      = Path("E:/AI_Employee_Vault")
SLIDES_URL = (VAULT / "demo" / "slides.html").as_uri()
PROFILE    = str(VAULT / ".secrets" / "browser_profile")

PAUSE_SHORT  = 3
PAUSE_MEDIUM = 5
PAUSE_LONG   = 7


# ── Helpers ───────────────────────────────────────────────────────────────────

def wait(secs=PAUSE_MEDIUM):
    time.sleep(secs)


def banner(page, step_num, title, subtitle="", position="bottom"):
    """Inject a floating chapter banner onto any page."""
    pos_css = "bottom:30px" if position == "bottom" else "top:24px"
    page.evaluate(f"""() => {{
        const old = document.getElementById('ai-demo-banner');
        if (old) old.remove();
        const d = document.createElement('div');
        d.id = 'ai-demo-banner';
        d.style.cssText = `
            position:fixed; {pos_css}; left:50%; transform:translateX(-50%);
            background:linear-gradient(135deg,#0f172a,#1e3a5f);
            color:#fff; padding:16px 36px; border-radius:14px;
            font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
            z-index:2147483647;
            box-shadow:0 20px 60px rgba(0,0,0,.6);
            border:1px solid rgba(99,179,237,.3);
            text-align:center; min-width:480px;
            backdrop-filter:blur(16px);
        `;
        d.innerHTML = `
            <div style="display:flex;align-items:center;gap:14px;justify-content:center">
                <div style="background:#3b82f6;border-radius:50%;width:30px;height:30px;
                            display:flex;align-items:center;justify-content:center;
                            font-weight:800;font-size:13px;flex-shrink:0">{step_num}</div>
                <div>
                    <div style="font-size:17px;font-weight:700;color:#e2e8f0">{title}</div>
                    <div style="font-size:12px;color:#94a3b8;margin-top:3px">{subtitle}</div>
                </div>
                <div style="margin-left:12px;background:rgba(59,130,246,.2);padding:3px 11px;
                            border-radius:20px;font-size:10px;color:#60a5fa;
                            border:1px solid rgba(59,130,246,.3);white-space:nowrap">
                    🤖 AI Employee
                </div>
            </div>
        `;
        document.body.appendChild(d);
    }}""")


def safe_goto(page, url, wait_until="domcontentloaded", timeout=20000):
    try:
        page.goto(url, wait_until=wait_until, timeout=timeout)
    except Exception as e:
        print(f"  [warn] Navigation: {str(e)[:120]}")
    # Let any post-navigation redirects settle
    try:
        page.wait_for_load_state("domcontentloaded", timeout=5000)
    except Exception:
        pass


def safe_banner(page, step_num, title, subtitle=""):
    try:
        banner(page, step_num, title, subtitle)
    except Exception as e:
        print(f"  [warn] Banner skipped: {str(e)[:80]}")


# ── Log HTML builder ──────────────────────────────────────────────────────────

def build_log_html():
    """Read today's JSON log and return a self-contained HTML string."""
    log_files = sorted((VAULT / "Logs").glob("2026-*.json"), reverse=True)
    entries = []
    for lf in log_files[:2]:
        try:
            entries += json.loads(lf.read_text(encoding="utf-8"))
        except Exception:
            pass
    entries = entries[:18]  # show latest 18

    rows = ""
    for e in entries:
        ts = e.get("timestamp", "")[:19].replace("T", " ")
        actor = e.get("actor", "")
        action = e.get("action_type", "")
        result = e.get("result", "")
        target = e.get("target", "")
        color = "#4ade80" if result == "success" else ("#f87171" if result == "error" else "#94a3b8")
        rows += f"""
        <tr>
          <td style="color:#64748b;font-size:13px;padding:10px 16px;white-space:nowrap">{ts}</td>
          <td style="color:#60a5fa;padding:10px 16px;font-weight:600">{actor}</td>
          <td style="color:#e2e8f0;padding:10px 16px">{action}</td>
          <td style="padding:10px 16px;overflow:hidden;max-width:280px;
                     white-space:nowrap;text-overflow:ellipsis;color:#94a3b8">{target}</td>
          <td style="padding:10px 16px"><span style="color:{color};font-weight:600">{result}</span></td>
        </tr>"""

    return f"""<!DOCTYPE html><html>
<head><meta charset="UTF-8">
<style>
  body{{background:#000;color:#fff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
       padding:60px;margin:0}}
  body::before{{content:'';position:fixed;inset:0;
    background:radial-gradient(ellipse 80% 40% at 50% -5%,rgba(59,130,246,.1),transparent);
    pointer-events:none}}
  .title{{font-size:13px;text-transform:uppercase;letter-spacing:2px;
          color:#60a5fa;margin-bottom:12px}}
  h2{{font-size:36px;font-weight:700;margin-bottom:8px}}
  .sub{{color:rgba(255,255,255,.4);font-size:15px;margin-bottom:36px}}
  table{{width:100%;border-collapse:collapse;
         background:rgba(255,255,255,.03);border-radius:12px;overflow:hidden;
         border:1px solid rgba(255,255,255,.07)}}
  thead tr{{background:rgba(255,255,255,.05)}}
  thead th{{padding:12px 16px;text-align:left;font-size:11px;text-transform:uppercase;
             letter-spacing:1px;color:rgba(255,255,255,.4);font-weight:600}}
  tbody tr:hover{{background:rgba(255,255,255,.03)}}
  tbody tr{{border-top:1px solid rgba(255,255,255,.04)}}
</style>
</head>
<body>
  <div class="title">📋 Audit Trail</div>
  <h2>Live Action Logs</h2>
  <p class="sub">Every action logged to /Logs/YYYY-MM-DD.json — tamper-proof audit trail</p>
  <table>
    <thead><tr>
      <th>Timestamp</th><th>Actor</th><th>Action</th><th>Target</th><th>Result</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
</body></html>"""


# ── Main Demo ─────────────────────────────────────────────────────────────────

def run_demo():
    log_html_path = VAULT / "demo" / "logs.html"
    log_html_path.write_text(build_log_html(), encoding="utf-8")

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            PROFILE,
            headless=False,
            args=["--start-maximized", "--disable-infobars"],
            no_viewport=True,
            slow_mo=80,
        )
        page = ctx.new_page()
        page.set_viewport_size({"width": 1920, "height": 1080})

        print("\n[DEMO] AI Employee Demo starting - start your screen recorder NOW\n")
        time.sleep(3)

        # ── SLIDE 1 — Intro ──────────────────────────────────────────────────
        print("[+] Slide 1: Intro")
        safe_goto(page, SLIDES_URL)
        page.evaluate("goToSlide(1)")
        wait(PAUSE_LONG)

        # ── SLIDE 2 — Capabilities ───────────────────────────────────────────
        print("[+] Slide 2: Capabilities")
        page.evaluate("nextSlide()")
        wait(PAUSE_LONG)

        # ── SLIDE 3 — Architecture ───────────────────────────────────────────
        print("[+] Slide 3: Architecture")
        page.evaluate("nextSlide()")
        wait(PAUSE_LONG)

        # ── SLIDE 4 — HITL ───────────────────────────────────────────────────
        print("[+] Slide 4: HITL Workflow")
        page.evaluate("nextSlide()")
        wait(PAUSE_LONG)

        # ── SLIDE 5 — Tech Stack ─────────────────────────────────────────────
        print("[+] Slide 5: Tech Stack")
        page.evaluate("nextSlide()")
        wait(PAUSE_MEDIUM)

        # ── GitHub ───────────────────────────────────────────────────────────
        print("[+] GitHub: source code")
        safe_goto(page, "https://github.com/NailaImran/E-commerce-AI-employee",
                  wait_until="domcontentloaded", timeout=30000)
        wait(PAUSE_SHORT)
        safe_banner(page, "→", "GitHub Repository",
               "Full source: MCP servers, watchers, skills, Playwright automation")
        wait(PAUSE_LONG)
        # scroll to show README
        page.evaluate("window.scrollTo({top: 600, behavior: 'smooth'})")
        wait(PAUSE_MEDIUM)

        # ── Audit Logs ───────────────────────────────────────────────────────
        print("[+] Logs: audit trail")
        safe_goto(page, log_html_path.as_uri())
        wait(PAUSE_SHORT)
        safe_banner(page, "→", "Audit Logs — /Logs/YYYY-MM-DD.json",
               "Every action logged: watchers, approvals, social posts, Odoo sync")
        wait(PAUSE_LONG)

        # ── Odoo — Sales Orders ──────────────────────────────────────────────
        print("[+] Odoo: sales orders")
        safe_goto(page, "https://mystore6.odoo.com/odoo/sales",
                  wait_until="domcontentloaded", timeout=30000)
        wait(PAUSE_MEDIUM)
        safe_banner(page, "→", "Odoo ERP — Sales Orders",
               "S00002: Sara Khan — Embroidered Lawn Suit + Chiffon Dupatta (PKR 11,407)")
        wait(PAUSE_LONG)

        # ── Odoo — Invoices ──────────────────────────────────────────────────
        print("[+] Odoo: invoices")
        safe_goto(page, "https://mystore6.odoo.com/odoo/accounting/customer-invoices",
                  wait_until="domcontentloaded", timeout=30000)
        wait(PAUSE_MEDIUM)
        safe_banner(page, "→", "Odoo ERP — Invoice INV/2026/00001",
               "Auto-created via XML-RPC — state: posted — payment: not_paid")
        wait(PAUSE_LONG)

        # ── LinkedIn ─────────────────────────────────────────────────────────
        print("[+] LinkedIn: hackathon post")
        safe_goto(page, "https://www.linkedin.com/in/naila-yaqoob-00ab72342/recent-activity/all/",
                  wait_until="domcontentloaded", timeout=30000)
        wait(PAUSE_MEDIUM)
        safe_banner(page, "→", "LinkedIn — Hackathon 0 Showcase Post",
               "Posted via LinkedIn API — HITL approved — urn:li:share:7433568447827050496")
        wait(PAUSE_LONG)

        # ── Instagram ────────────────────────────────────────────────────────
        print("[+] Instagram: fashion post")
        safe_goto(page, "https://www.instagram.com/nailayaqoob86/",
                  wait_until="domcontentloaded", timeout=30000)
        wait(PAUSE_MEDIUM)
        safe_banner(page, "→", "Instagram — Fashion Product Post",
               "Published via Meta Graph API — Post ID: 17973975764841305")
        wait(PAUSE_LONG)

        # ── SLIDE 6 — Gold Tier Outro ────────────────────────────────────────
        print("[+] Slide 6: Gold Tier badge")
        safe_goto(page, SLIDES_URL)
        page.evaluate("goToSlide(6)")
        wait(PAUSE_LONG + 2)

        print("\n[DONE] Demo complete - stop your screen recorder\n")
        wait(3)
        ctx.close()


if __name__ == "__main__":
    run_demo()
