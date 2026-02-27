#!/usr/bin/env python3
"""
post_to_twitter.py — Twitter/X posting script for E-commerce AI Employee

Called by approval_watcher.py when a TWITTER_*.md file appears in /Approved/.
Reads the approved tweet text from the file and posts it via Twitter API v2 using tweepy.

Usage:
    # Post from an approved HITL file:
    python post_to_twitter.py --file E:/AI_Employee_Vault/Approved/TWITTER_2026-02-23.md

    # Post inline text (for testing):
    python post_to_twitter.py --text "Your tweet here" --vault E:/AI_Employee_Vault

    # Dry-run (validate without posting):
    python post_to_twitter.py --file path/to/file.md --dry-run

Requirements:
    pip install tweepy python-dotenv
"""

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TwitterPoster")

VAULT_PATH = Path(os.getenv("VAULT_PATH", "E:/AI_Employee_Vault"))


def load_env(vault: Path):
    """Load .env file from vault root."""
    env_file = vault / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            if key.strip() not in os.environ:
                os.environ[key.strip()] = value.strip()


def get_twitter_client():
    """Create and return a tweepy Client for Twitter API v2."""
    try:
        import tweepy
    except ImportError:
        logger.error("tweepy not installed. Run: pip install tweepy")
        sys.exit(1)

    api_key = os.getenv("TWITTER_API_KEY")
    api_secret = os.getenv("TWITTER_API_SECRET")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

    if not all([api_key, api_secret, access_token, access_token_secret]):
        logger.error(
            "Twitter credentials not set. Add to .env:\n"
            "  TWITTER_API_KEY\n"
            "  TWITTER_API_SECRET\n"
            "  TWITTER_ACCESS_TOKEN\n"
            "  TWITTER_ACCESS_TOKEN_SECRET\n"
            "See .claude/skills/twitter-poster/references/twitter_api.md for setup."
        )
        sys.exit(1)

    return tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_token_secret,
    )


def extract_tweet_text(filepath: Path) -> str:
    """Extract tweet text from an approved HITL markdown file."""
    content = filepath.read_text(encoding="utf-8", errors="ignore")

    # Strip YAML frontmatter
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            content = content[end + 3:].strip()

    # Find ## Draft Tweet section
    m = re.search(r"##\s+Draft Tweet\s*\n+(.*?)(?:\n\n---|\Z)", content, re.DOTALL)
    if m:
        text = m.group(1).strip()
        # Remove trailing "Move to /Approved/" instruction if it slipped in
        text = re.sub(r"\n---.*", "", text, flags=re.DOTALL).strip()
        return text

    # Fallback: return everything after frontmatter
    return content.strip()


def write_audit_log(vault: Path, action_type: str, target: str, result: str, **kwargs):
    """Append JSON audit entry to /Logs/YYYY-MM-DD.json."""
    logs_dir = vault / "Logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    day_str = datetime.now().strftime("%Y-%m-%d")
    log_file = logs_dir / f"{day_str}.json"
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action_type": action_type,
        "actor": "twitter-poster",
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


def write_twitter_log(vault: Path, tweet_text: str, tweet_id: str, tweet_url: str):
    """Append to /Logs/twitter_posts.md for human-readable history."""
    log_file = vault / "Logs" / "twitter_posts.md"
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n## {now}\n**ID**: {tweet_id}\n**URL**: {tweet_url}\n\n{tweet_text}\n\n---"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(entry)


def move_to_done(filepath: Path, vault: Path):
    done = vault / "Done"
    done.mkdir(exist_ok=True)
    dest = done / filepath.name
    filepath.rename(dest)
    logger.info(f"Moved to /Done/: {filepath.name}")


def main():
    parser = argparse.ArgumentParser(description="Post tweet to Twitter/X")
    parser.add_argument("--file", help="Path to TWITTER_*.md approval file")
    parser.add_argument("--text", help="Tweet text (alternative to --file)")
    parser.add_argument("--vault", default=str(VAULT_PATH), help="Vault path")
    parser.add_argument("--dry-run", action="store_true", help="Validate without posting")
    args = parser.parse_args()

    vault = Path(args.vault)
    load_env(vault)

    # Determine tweet text
    if args.file:
        filepath = Path(args.file)
        if not filepath.exists():
            logger.error(f"File not found: {filepath}")
            sys.exit(1)
        tweet_text = extract_tweet_text(filepath)
    elif args.text:
        tweet_text = args.text
        filepath = None
    else:
        logger.error("Provide --file or --text")
        sys.exit(1)

    if not tweet_text:
        logger.error("Could not extract tweet text from file")
        sys.exit(1)

    if len(tweet_text) > 280:
        logger.error(f"Tweet is {len(tweet_text)} chars (max 280). Shorten it.")
        sys.exit(1)

    logger.info(f"Tweet ({len(tweet_text)}/280 chars):\n{tweet_text}")

    if args.dry_run:
        logger.info("[DRY RUN] Would post the tweet above. No action taken.")
        write_audit_log(vault, "post_tweet", "dry_run", "dry_run", char_count=len(tweet_text))
        return

    # Post tweet
    client = get_twitter_client()
    try:
        response = client.create_tweet(text=tweet_text)
        tweet_id = response.data["id"]
        tweet_url = f"https://x.com/i/web/status/{tweet_id}"
        logger.info(f"[OK] Tweet posted: {tweet_url}")

        write_audit_log(
            vault, "post_tweet", tweet_id, "success",
            tweet_url=tweet_url, char_count=len(tweet_text)
        )
        write_twitter_log(vault, tweet_text, tweet_id, tweet_url)

        if filepath and filepath.exists():
            move_to_done(filepath, vault)

    except Exception as e:
        logger.error(f"Failed to post tweet: {e}")
        write_audit_log(vault, "post_tweet", "error", "error", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
