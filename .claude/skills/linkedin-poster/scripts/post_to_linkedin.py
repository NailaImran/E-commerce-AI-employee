#!/usr/bin/env python3
"""
LinkedIn Post Publisher — E-commerce AI Employee (Silver Tier)

Posts content to LinkedIn using the LinkedIn API v2.
Access token must be stored in E:/AI_Employee_Vault/.secrets/linkedin_token.txt

Usage:
    python post_to_linkedin.py --post "Your post text" --token-file E:/AI_Employee_Vault/.secrets/linkedin_token.txt
    python post_to_linkedin.py --file E:/AI_Employee_Vault/Approved/LINKEDIN_2026-02-21.md --token-file ...
    python post_to_linkedin.py --post "Test post" --token-file ... --dry-run

Requirements:
    pip install requests

Token scopes needed: w_member_social, r_liteprofile
See references/linkedin_api.md for setup instructions.
"""

import argparse
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("LinkedInPoster")

LINKEDIN_API_BASE = "https://api.linkedin.com/v2"


def get_person_urn(access_token: str) -> str:
    """Fetch the authenticated user's Person URN."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "LinkedIn-Version": "202304",
    }
    resp = requests.get(f"{LINKEDIN_API_BASE}/userinfo", headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    sub = data.get("sub", "")
    if not sub:
        raise ValueError("Could not get person URN from LinkedIn userinfo endpoint")
    return f"urn:li:person:{sub}"


def post_to_linkedin(access_token: str, person_urn: str, text: str, dry_run: bool = False) -> dict:
    """Publish a text post to LinkedIn."""
    payload = {
        "author": person_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }

    if dry_run:
        logger.info(f"[DRY RUN] Would post to LinkedIn ({person_urn}):\n\n{text}")
        return {"id": "dry-run-post-id"}

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    resp = requests.post(
        f"{LINKEDIN_API_BASE}/ugcPosts",
        headers=headers,
        json=payload,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def extract_post_from_approval_file(filepath: Path) -> str:
    """Extract post content from a LINKEDIN_*.md approval file."""
    text = filepath.read_text(encoding="utf-8")
    match = re.search(r"## Draft Post\n\n(.*?)\n\n---", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Fallback: everything after the frontmatter
    body = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.DOTALL).strip()
    return body


def log_post(vault: Path, post_text: str, post_id: str):
    """Append to LinkedIn post log."""
    log_file = vault / "Logs" / "linkedin_posts.md"
    entry = f"\n## {datetime.now().strftime('%Y-%m-%d %H:%M')}\n**Post ID**: {post_id}\n\n{post_text}\n\n---"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(entry)
    logger.info(f"Post logged to {log_file}")


def main():
    parser = argparse.ArgumentParser(description="Post to LinkedIn for E-commerce AI Employee")
    parser.add_argument("--post", help="Post text (use this OR --file)")
    parser.add_argument("--file", help="Path to LINKEDIN_*.md approval file")
    parser.add_argument("--token-file", required=True, help="Path to file containing LinkedIn access token")
    parser.add_argument("--vault", default="E:/AI_Employee_Vault")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    token_path = Path(args.token_file)
    if not token_path.exists():
        logger.error(f"Token file not found: {token_path}")
        logger.error("Store your LinkedIn access token at E:/AI_Employee_Vault/.secrets/linkedin_token.txt")
        sys.exit(1)

    access_token = token_path.read_text().strip()
    vault = Path(args.vault)

    # Get post content
    if args.file:
        post_text = extract_post_from_approval_file(Path(args.file))
    elif args.post:
        post_text = args.post
    else:
        logger.error("Provide either --post 'text' or --file path/to/approval.md")
        sys.exit(1)

    if not post_text:
        logger.error("Post content is empty.")
        sys.exit(1)

    # Get Person URN
    try:
        logger.info("Fetching LinkedIn Person URN...")
        person_urn = get_person_urn(access_token)
        logger.info(f"Person URN: {person_urn}")
    except Exception as e:
        logger.error(f"Failed to get Person URN: {e}")
        sys.exit(1)

    # Post
    try:
        result = post_to_linkedin(access_token, person_urn, post_text, args.dry_run)
        post_id = result.get("id", "unknown")
        logger.info(f"Posted successfully. Post ID: {post_id}")
        log_post(vault, post_text, post_id)

        # Move approval file to Done if used
        if args.file:
            src = Path(args.file)
            done_dir = vault / "Done"
            done_dir.mkdir(exist_ok=True)
            src.rename(done_dir / src.name)
            logger.info(f"Moved {src.name} to /Done/")

    except requests.HTTPError as e:
        logger.error(f"LinkedIn API error: {e.response.status_code} — {e.response.text}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to post: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
