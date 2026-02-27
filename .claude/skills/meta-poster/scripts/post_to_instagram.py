#!/usr/bin/env python3
"""
post_to_instagram.py — Instagram Business posting script for E-commerce AI Employee

Called by approval_watcher.py when an INSTAGRAM_*.md file appears in /Approved/.
Posts to the Instagram Business account linked to the Facebook Page via Meta Graph API v21.0.

Instagram posting is a two-step process:
  1. Create a media container (upload image + caption)
  2. Publish the container

Usage:
    python post_to_instagram.py --file E:/AI_Employee_Vault/Approved/INSTAGRAM_2026-02-23.md
    python post_to_instagram.py --caption "Caption text" --image-url "https://..." --vault E:/AI_Employee_Vault
    python post_to_instagram.py --file path/to/file.md --dry-run

Requirements:
    pip install requests
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
logger = logging.getLogger("InstagramPoster")

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
    ig_id = os.getenv("META_INSTAGRAM_ACCOUNT_ID")
    if not token:
        logger.error(
            "META_PAGE_ACCESS_TOKEN not set in .env\n"
            "See .claude/skills/meta-poster/references/meta_api.md"
        )
        sys.exit(1)
    if not ig_id:
        logger.error(
            "META_INSTAGRAM_ACCOUNT_ID not set in .env\n"
            "Find it in: Meta Business Suite → Instagram Account → Account ID"
        )
        sys.exit(1)
    return token, ig_id


def extract_post_content(filepath: Path) -> dict:
    """Extract caption and image_url from INSTAGRAM_*.md approval file."""
    content = filepath.read_text(encoding="utf-8", errors="ignore")

    image_url = None
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            fm = content[3:end]
            m = re.search(r"image_url:\s*(.+)", fm)
            if m and m.group(1).strip() not in ("", "(optional)", "null"):
                image_url = m.group(1).strip()
            content = content[end + 3:].strip()

    # Find ## Draft Caption section
    m = re.search(r"##\s+Draft Caption\s*\n+(.*?)(?:\n\n---|\Z)", content, re.DOTALL)
    if m:
        caption = m.group(1).strip()
        caption = re.sub(r"\n---.*", "", caption, flags=re.DOTALL).strip()
    else:
        caption = content.strip()

    return {"caption": caption, "image_url": image_url}


def create_media_container(token: str, ig_id: str, caption: str, image_url: str) -> str:
    url = f"{GRAPH_BASE}/{ig_id}/media"
    resp = requests.post(url, data={
        "image_url": image_url,
        "caption": caption,
        "access_token": token,
    })
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Container creation failed: {data['error']['message']}")
    return data["id"]


def publish_media_container(token: str, ig_id: str, container_id: str) -> str:
    url = f"{GRAPH_BASE}/{ig_id}/media_publish"
    resp = requests.post(url, data={
        "creation_id": container_id,
        "access_token": token,
    })
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Publish failed: {data['error']['message']}")
    return data["id"]


def write_audit_log(vault: Path, action_type: str, target: str, result: str, **kwargs):
    logs_dir = vault / "Logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / f"{datetime.now().strftime('%Y-%m-%d')}.json"
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action_type": action_type,
        "actor": "meta-poster/instagram",
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


def write_meta_log(vault: Path, media_id: str, post_url: str, caption: str):
    log_file = vault / "Logs" / "meta_posts.md"
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n## [Instagram] {now}\n**ID**: {media_id}\n**URL**: {post_url}\n\n{caption}\n\n---"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(entry)


def move_to_done(filepath: Path, vault: Path):
    done = vault / "Done"
    done.mkdir(exist_ok=True)
    filepath.rename(done / filepath.name)
    logger.info(f"Moved to /Done/: {filepath.name}")


def main():
    parser = argparse.ArgumentParser(description="Post to Instagram Business via Meta Graph API")
    parser.add_argument("--file", help="Path to INSTAGRAM_*.md approval file")
    parser.add_argument("--caption", help="Instagram caption (alternative to --file)")
    parser.add_argument("--image-url", help="Public image URL (required for Instagram)")
    parser.add_argument("--vault", default=str(VAULT_PATH))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    vault = Path(args.vault)
    load_env(vault)
    token, ig_id = get_credentials()

    if args.file:
        filepath = Path(args.file)
        if not filepath.exists():
            logger.error(f"File not found: {filepath}")
            sys.exit(1)
        content = extract_post_content(filepath)
        caption = content["caption"]
        image_url = content["image_url"] or args.image_url
    elif args.caption:
        filepath = None
        caption = args.caption
        image_url = args.image_url
    else:
        logger.error("Provide --file or --caption")
        sys.exit(1)

    if not caption:
        logger.error("Could not extract caption from file")
        sys.exit(1)

    if not image_url:
        logger.error(
            "Instagram requires an image URL. Add 'image_url: https://...' to the "
            "INSTAGRAM_*.md frontmatter, or pass --image-url"
        )
        sys.exit(1)

    logger.info(f"Instagram post:\nImage: {image_url}\nCaption ({len(caption)} chars):\n{caption[:200]}")

    if args.dry_run:
        logger.info("[DRY RUN] Would post the content above. No action taken.")
        write_audit_log(vault, "post_to_instagram", "dry_run", "dry_run",
                        caption_preview=caption[:80], image_url=image_url)
        return

    try:
        logger.info("Step 1/2: Creating media container...")
        container_id = create_media_container(token, ig_id, caption, image_url)
        logger.info(f"Container created: {container_id}")

        logger.info("Step 2/2: Publishing media container...")
        media_id = publish_media_container(token, ig_id, container_id)
        post_url = f"https://www.instagram.com/p/{media_id}/"
        logger.info(f"[OK] Instagram post published: {post_url}")

        write_audit_log(vault, "post_to_instagram", media_id, "success",
                        post_url=post_url, image_url=image_url)
        write_meta_log(vault, media_id, post_url, caption)

        if filepath and filepath.exists():
            move_to_done(filepath, vault)

    except Exception as e:
        logger.error(f"Failed to post to Instagram: {e}")
        write_audit_log(vault, "post_to_instagram", "error", "error", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
