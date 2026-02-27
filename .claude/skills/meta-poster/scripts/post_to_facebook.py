#!/usr/bin/env python3
"""
post_to_facebook.py — Facebook Page posting script for E-commerce AI Employee

Called by approval_watcher.py when a FACEBOOK_*.md file appears in /Approved/.
Posts to the configured Facebook Page via Meta Graph API v21.0.

Usage:
    python post_to_facebook.py --file E:/AI_Employee_Vault/Approved/FACEBOOK_2026-02-23.md
    python post_to_facebook.py --message "Post text" --vault E:/AI_Employee_Vault
    python post_to_facebook.py --file path/to/file.md --dry-run

Requirements:
    pip install requests python-dotenv
"""

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("FacebookPoster")

GRAPH_API_VERSION = "v21.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"
VAULT_PATH = Path(os.getenv("VAULT_PATH", "E:/AI_Employee_Vault"))


def load_env(vault: Path):
    env_file = vault / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            if key.strip() not in os.environ:
                os.environ[key.strip()] = value.strip()


def get_credentials():
    token = os.getenv("META_PAGE_ACCESS_TOKEN")
    page_id = os.getenv("META_PAGE_ID")
    if not token:
        logger.error(
            "META_PAGE_ACCESS_TOKEN not set in .env\n"
            "See .claude/skills/meta-poster/references/meta_api.md for setup."
        )
        sys.exit(1)
    if not page_id:
        logger.error("META_PAGE_ID not set in .env")
        sys.exit(1)
    return token, page_id


def extract_post_content(filepath: Path) -> dict:
    """Extract message, image_url, link from FACEBOOK_*.md approval file."""
    content = filepath.read_text(encoding="utf-8", errors="ignore")

    # Parse frontmatter for image_url
    image_url = None
    link = None
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            fm = content[3:end]
            m = re.search(r"image_url:\s*(.+)", fm)
            if m and m.group(1).strip() not in ("", "(optional)", "null"):
                image_url = m.group(1).strip()
            lm = re.search(r"link:\s*(.+)", fm)
            if lm and lm.group(1).strip() not in ("", "(optional)", "null"):
                link = lm.group(1).strip()
            content = content[end + 3:].strip()

    # Find ## Draft Post section
    m = re.search(r"##\s+Draft Post\s*\n+(.*?)(?:\n\n---|\Z)", content, re.DOTALL)
    if m:
        message = m.group(1).strip()
        message = re.sub(r"\n---.*", "", message, flags=re.DOTALL).strip()
    else:
        message = content.strip()

    return {"message": message, "image_url": image_url, "link": link}


def post_photo(token: str, page_id: str, message: str, image_url: str) -> str:
    url = f"{GRAPH_BASE}/{page_id}/photos"
    resp = requests.post(url, data={
        "caption": message,
        "url": image_url,
        "access_token": token,
    })
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Graph API error: {data['error']['message']}")
    return data.get("post_id") or data.get("id")


def post_feed(token: str, page_id: str, message: str, link: str = None) -> str:
    url = f"{GRAPH_BASE}/{page_id}/feed"
    params = {"message": message, "access_token": token}
    if link:
        params["link"] = link
    resp = requests.post(url, data=params)
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Graph API error: {data['error']['message']}")
    return data.get("id")


def write_audit_log(vault: Path, action_type: str, target: str, result: str, **kwargs):
    logs_dir = vault / "Logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / f"{datetime.now().strftime('%Y-%m-%d')}.json"
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action_type": action_type,
        "actor": "meta-poster/facebook",
        "target": target,
        "result": result,
        **kwargs,
    }
    existing = []
    if log_file.exists():
        try:
            existing = json.loads(log_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    existing.append(entry)
    log_file.write_text(json.dumps(existing, indent=2), encoding="utf-8")


def write_meta_log(vault: Path, platform: str, post_id: str, post_url: str, message: str):
    log_file = vault / "Logs" / "meta_posts.md"
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n## [{platform}] {now}\n**ID**: {post_id}\n**URL**: {post_url}\n\n{message}\n\n---"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(entry)


def move_to_done(filepath: Path, vault: Path):
    done = vault / "Done"
    done.mkdir(exist_ok=True)
    filepath.rename(done / filepath.name)
    logger.info(f"Moved to /Done/: {filepath.name}")


def main():
    parser = argparse.ArgumentParser(description="Post to Facebook Page via Meta Graph API")
    parser.add_argument("--file", help="Path to FACEBOOK_*.md approval file")
    parser.add_argument("--message", help="Post message (alternative to --file)")
    parser.add_argument("--image-url", help="Optional image URL")
    parser.add_argument("--link", help="Optional link URL")
    parser.add_argument("--vault", default=str(VAULT_PATH))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    vault = Path(args.vault)
    load_env(vault)
    token, page_id = get_credentials()

    if args.file:
        filepath = Path(args.file)
        if not filepath.exists():
            logger.error(f"File not found: {filepath}")
            sys.exit(1)
        content = extract_post_content(filepath)
        message = content["message"]
        image_url = content["image_url"] or args.image_url
        link = content["link"] or args.link
    elif args.message:
        filepath = None
        message = args.message
        image_url = args.image_url
        link = args.link
    else:
        logger.error("Provide --file or --message")
        sys.exit(1)

    if not message:
        logger.error("Could not extract post message")
        sys.exit(1)

    logger.info(f"Facebook post ({len(message)} chars):\n{message[:200]}")
    if image_url:
        logger.info(f"With image: {image_url}")

    if args.dry_run:
        logger.info("[DRY RUN] Would post the content above. No action taken.")
        write_audit_log(vault, "post_to_facebook_page", "dry_run", "dry_run",
                        message_preview=message[:80])
        return

    try:
        if image_url:
            post_id = post_photo(token, page_id, message, image_url)
        else:
            post_id = post_feed(token, page_id, message, link)

        post_url = f"https://www.facebook.com/{post_id}"
        logger.info(f"[OK] Facebook post published: {post_url}")

        write_audit_log(vault, "post_to_facebook_page", post_id, "success", post_url=post_url)
        write_meta_log(vault, "Facebook", post_id, post_url, message)

        if filepath and filepath.exists():
            move_to_done(filepath, vault)

    except Exception as e:
        logger.error(f"Failed to post to Facebook: {e}")
        write_audit_log(vault, "post_to_facebook_page", "error", "error", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
