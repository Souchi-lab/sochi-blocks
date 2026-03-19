#!/usr/bin/env python3
"""
Read tmp/reel_queue.txt and post Instagram Reels for each puzzle.

Run this ~20 minutes after auto_publish.py so that cover images (3d_x.png)
are guaranteed to be live on GitHub Pages before the Instagram API fetches them.

Usage:
  poetry run python scripts/post_reel_from_queue.py
"""

import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
QUEUE_FILE = PROJECT_ROOT / "tmp" / "reel_queue.txt"
DOCS_DIR = PROJECT_ROOT / "docs"
PAGES_BASE_URL = "https://souchi-lab.github.io/sochi-blocks"
_LOG = "[Reel Queue]"

# Wait up to 10 minutes for each cover image (GitHub Pages can be slow)
COVER_MAX_WAIT_SEC = 600
COVER_RETRY_INTERVAL_SEC = 20


def wait_for_cover(puzzle_code: str) -> bool:
    """Poll GitHub Pages until 3d_x.png is accessible, or timeout."""
    date_str, seq = puzzle_code.split("_", 1)
    cover_url = f"{PAGES_BASE_URL}/images/{date_str}/{seq}/3d_x.png"
    max_retries = COVER_MAX_WAIT_SEC // COVER_RETRY_INTERVAL_SEC

    print(f"    Checking: {cover_url}")
    for attempt in range(1, max_retries + 1):
        try:
            with urllib.request.urlopen(cover_url) as resp:
                if resp.getcode() == 200:
                    print(f"    [OK] Cover is live! (attempt {attempt})")
                    return True
        except (urllib.error.HTTPError, urllib.error.URLError):
            pass
        print(f"    [...] Not live yet ({attempt}/{max_retries}) — retry in {COVER_RETRY_INTERVAL_SEC}s...")
        time.sleep(COVER_RETRY_INTERVAL_SEC)

    return False


def main():
    if not QUEUE_FILE.exists():
        print(f"{_LOG} ERROR: Queue file not found: {QUEUE_FILE}")
        print(f"  Make sure auto_publish.py has run first.")
        sys.exit(1)

    codes = [
        line.strip()
        for line in QUEUE_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not codes:
        print(f"{_LOG} Queue file is empty. Nothing to post.")
        QUEUE_FILE.unlink()
        sys.exit(0)

    print(f"{_LOG} {len(codes)} puzzle(s) queued for Reel posting:")
    for code in codes:
        print(f"  - {code}")

    ok_count = 0
    for code in codes:
        print(f"\n{_LOG} [{code}] Starting...")

        # Derive asset directory from puzzle code (e.g. 20260314_001 → docs/images/20260314/001)
        date_str, seq = code.split("_", 1)
        img_dir = DOCS_DIR / "images" / date_str / seq
        if not img_dir.exists():
            print(f"  ERROR: Asset directory not found: {img_dir} — skipping.")
            continue

        # Wait for cover image to be live on GitHub Pages
        if not wait_for_cover(code):
            print(f"  ERROR: Cover image not live after {COVER_MAX_WAIT_SEC}s timeout — skipping {code}.")
            continue

        # Post Reel
        try:
            subprocess.run(
                [
                    "poetry", "run", "python",
                    "scripts/publish_instagram_reel.py",
                    "--puzzle-id", code,
                    "--dir", str(img_dir),
                    "--base-url", PAGES_BASE_URL,
                ],
                check=True,
                cwd=str(PROJECT_ROOT),
            )
            ok_count += 1
            print(f"  [OK] Reel posted: {code}")
        except Exception as e:
            print(f"  WARN: Reel post failed for {code}: {e}")

    # Clean up queue file
    QUEUE_FILE.unlink()
    print(f"\n{_LOG} Done. {ok_count}/{len(codes)} Reels posted successfully.")
    print(f"  Queue file deleted.")


if __name__ == "__main__":
    main()
