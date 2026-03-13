#!/usr/bin/env python3
"""
[Instagram Reel] Post a SoChi BLOCKS puzzle video as an Instagram Reel.

SNS Strategy:
  Instagram Reel → Brand exposure / Ongoing follower reach
  - Full video (0-12s) with answer revealed (saves/shares drive engagement)
  - Video: {puzzle_id}_instagram.mp4 → {puzzle_id}_full.mp4 (fallback)
  - Caption: caption_instagram.txt

Usage:
  python scripts/publish_instagram_reel.py \\
    --puzzle-id 20260312_004 \\
    --dir docs/images/20260312/004/ \\
    --base-url https://souchi-lab.github.io/sochi-blocks
"""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).resolve().parent))
from publish_instagram import (
    get_instagram_config,
    request_with_retry,
    wait_for_container,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SNS_VIDEOS_DIR = PROJECT_ROOT / "docs" / "sns_videos"

_LOG = "[Instagram Reel]"


def post_reel(puzzle_id: str, asset_dir: Path, base_url: str) -> bool:
    ig_id, access_token = get_instagram_config()
    if not ig_id:
        return False

    # Caption: prefer instagram-specific, fall back to generic
    caption_path = asset_dir / "caption_instagram.txt"
    if not caption_path.exists():
        caption_path = asset_dir / "caption.txt"
    if not caption_path.exists():
        print(f"{_LOG} ERROR: No caption file found in {asset_dir}")
        print(f"  Expected: caption_instagram.txt or caption.txt")
        return False

    # Video: prefer _instagram.mp4 (full with answer), then _full.mp4
    video_candidates = [
        SNS_VIDEOS_DIR / f"{puzzle_id}_instagram.mp4",
        SNS_VIDEOS_DIR / f"{puzzle_id}_full.mp4",
        SNS_VIDEOS_DIR / f"{puzzle_id}_teaser.mp4",
    ]
    video_file = next((p for p in video_candidates if p.exists()), None)
    if not video_file:
        print(f"{_LOG} ERROR: No video found for {puzzle_id}")
        print(f"  Searched: {[str(c) for c in video_candidates]}")
        return False

    caption = caption_path.read_text(encoding="utf-8")
    video_url = f"{base_url}/sns_videos/{video_file.name}"

    print(f"{_LOG} Posting Reel for {puzzle_id}")
    print(f"  Video:   {video_file.name}")
    print(f"  Caption: {caption_path.name}")
    print(f"  URL:     {video_url}")

    # Cover image: use 3d_x.png as the Reel thumbnail
    cover_url = None
    cover_img = asset_dir / "3d_x.png"
    if cover_img.exists():
        # Derive public URL from asset_dir relative to docs/
        parts = asset_dir.resolve().parts
        if "docs" in parts:
            idx = parts.index("docs")
            rel_url = "/".join(parts[idx + 1:]) + "/3d_x.png"
            cover_url = f"{base_url}/{rel_url}".replace("//", "/").replace("https:/", "https://")
            print(f"  Cover:   {cover_img.name}  → {cover_url}")

    # Step 1: Create Reels container
    api_url = f"https://graph.facebook.com/v21.0/{ig_id}/media"
    payload = {
        "access_token": access_token,
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "share_to_feed": "true",
    }
    if cover_url:
        payload["cover_url"] = cover_url
    res = request_with_retry("POST", api_url, data=payload)
    if "id" not in res:
        print(f"{_LOG} ERROR creating container: {res}")
        return False

    container_id = res["id"]
    print(f"{_LOG} Container created: {container_id}")

    # Step 2: Wait for processing
    if not wait_for_container(ig_id, access_token, container_id, timeout=300):
        return False

    # Step 3: Publish
    api_url = f"https://graph.facebook.com/v21.0/{ig_id}/media_publish"
    payload = {"access_token": access_token, "creation_id": container_id}
    res = request_with_retry("POST", api_url, data=payload)
    if "id" not in res:
        print(f"{_LOG} ERROR publishing: {res}")
        return False

    print(f"{_LOG} Successfully posted! Post ID: {res['id']}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="[Instagram Reel] Post a SoChi BLOCKS puzzle Reel",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
SNS Strategy: Instagram Reel → Brand exposure
  Full video (0-12s) with answer, drives saves and shares.
""",
    )
    parser.add_argument("--puzzle-id", required=True, help="e.g. 20260312_004")
    parser.add_argument("--dir", required=True, help="Path to asset directory (for caption)")
    parser.add_argument("--base-url", required=True, help="Public base URL for media assets")
    args = parser.parse_args()

    asset_dir = Path(args.dir)
    if not asset_dir.is_dir():
        print(f"{_LOG} ERROR: {asset_dir} is not a directory.")
        sys.exit(1)

    ok = post_reel(args.puzzle_id, asset_dir, args.base_url)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
