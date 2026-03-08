#!/usr/bin/env python3
"""
Post a SoChi BLOCKS puzzle to Twitter (X).
Requires credentials in .env:
  TWITTER_CONSUMER_KEY
  TWITTER_CONSUMER_SECRET
  TWITTER_ACCESS_TOKEN
  TWITTER_ACCESS_TOKEN_SECRET

Usage:
  python scripts/publish_twitter.py --dir docs/images/20260307/001/
"""

import argparse
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

try:
    import tweepy
except ImportError:
    print("Error: 'tweepy' library not found. Please run: poetry add tweepy")
    sys.exit(1)

# Load .env
load_dotenv()

def get_twitter_client():
    """Authenticate and return tweepy clients for v1.1 (media) and v2 (tweet)."""
    consumer_key = os.getenv("TWITTER_CONSUMER_KEY")
    consumer_secret = os.getenv("TWITTER_CONSUMER_SECRET")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

    if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
        print("Error: Missing Twitter credentials in .env")
        return None, None

    # V1.1 Client (needed for media upload)
    auth = tweepy.OAuth1UserHandler(consumer_key, consumer_secret, access_token, access_token_secret)
    api_v1 = tweepy.API(auth)

    # V2 Client (needed for tweeting)
    client_v2 = tweepy.Client(
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
        access_token_secret=access_token_secret
    )
    
    return api_v1, client_v2

def post_to_twitter(asset_dir: Path, link_only: bool = False, share_url: str | None = None):
    """Post images and caption in a main tweet, then reply with a video if it exists."""
    api_v1, client_v2 = get_twitter_client()
    if not api_v1:
        return False

    caption_path = asset_dir / "caption_twitter.txt"
    if not caption_path.exists():
        # Fallback to old format
        caption_path = asset_dir / "caption.txt"
    
    if not caption_path.exists():
        print(f"Error: No caption file found in {asset_dir}")
        return False

    with open(caption_path, "r", encoding="utf-8") as f:
        caption = f.read()

    # Find media files
    video_path = next(asset_dir.glob("*.mp4"), None)
    # Image for OG tag (layer.png)
    image_paths = [] # Initialize image_paths
    if not link_only:
        # Target images in specific order: layer.png, 3d_x.png, 3d_y.png
        image_names = ["layer.png", "3d_x.png", "3d_y.png"]
        for name in image_names:
            p = asset_dir / name
            if p.exists():
                image_paths.append(p)
        
        # Also grab any other pngs just in case
        for p in asset_dir.glob("*.png"):
            if p not in image_paths and len(image_paths) < 4:
                image_paths.append(p)

    # Append URL to caption if provided (and not already in caption)
    if share_url and share_url not in caption:
        # Check if the caption already has a placeholder URL we might want to replace, 
        # but for simplicity, we'll just append if missing.
        if "Try it here:" in caption:
            # If our template's "Try it here:" is there but with viewer URL, it's safer to just skip appending
            # or replace it. For now, if share_url is explicitly passed, let's assume it should be there.
            pass
        else:
            caption += f"\n\nTry it here: {share_url} 🧩"

    try:
        if link_only:
            print("Posting link-only tweet (Free API mode)...")
            client_v2.create_tweet(text=caption)
            print("Tweet posted successfully!")
            return True

        # Step 1: Post Main Tweet with Images
        main_media_ids = []
        if image_paths:
            print(f"Uploading {len(image_paths)} images for main tweet...")
            for img_path in image_paths:
                media = api_v1.media_upload(filename=str(img_path))
                main_media_ids.append(media.media_id)
        
        print("Creating main tweet...")
        main_response = client_v2.create_tweet(text=caption, media_ids=main_media_ids if main_media_ids else None)
        main_tweet_id = main_response.data['id']
        print(f"Main tweet posted! ID: {main_tweet_id}")

        # Step 2: Post Reply with Video (Twitter doesn't allow video + images in one tweet)
        if video_path:
            print(f"Uploading video for reply: {video_path.name}...")
            video_media = api_v1.media_upload(filename=str(video_path), media_category="tweet_video")
            
            print("Creating reply tweet with video...")
            reply_text = "Watch the solution! 🎬 #SoChiBLOCKS"
            client_v2.create_tweet(
                text=reply_text,
                media_ids=[video_media.media_id],
                in_reply_to_tweet_id=main_tweet_id
            )
            print("Reply tweet with video posted!")

        return True

    except Exception as e:
        print(f"Error during posting to Twitter: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Publish puzzle to Twitter")
    parser.add_argument("--dir", required=True, help="Path to asset directory")
    parser.add_argument("--link-only", action="store_true", help="Post only text and link (no media upload)")
    parser.add_argument("--url", help="Shareable URL to include in tweet")
    args = parser.parse_args()

    asset_dir = Path(args.dir)
    if not asset_dir.is_dir():
        print(f"Error: {asset_dir} is not a directory.")
        sys.exit(1)

    post_to_twitter(asset_dir, link_only=args.link_only, share_url=args.url)

if __name__ == "__main__":
    main()
