#!/usr/bin/env python3
"""
Post a SoChi BLOCKS puzzle to Instagram.
Requires credentials in .env:
  INSTAGRAM_BUSINESS_ACCOUNT_ID
  FACEBOOK_PAGE_ACCESS_TOKEN

Usage:
  python scripts/publish_instagram.py --dir docs/images/20260307/001/ --base-url https://souchi-lab.github.io/sochi-blocks
"""

import argparse
import os
import sys
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load .env
load_dotenv()

def get_instagram_config():
    ig_id = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")
    access_token = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")

    if not all([ig_id, access_token]):
        print("Error: Missing Instagram credentials in .env")
        return None, None
    return ig_id, access_token

def request_with_retry(method, url, max_retries=3, **kwargs):
    """Make an API request with retry logic for transient errors."""
    for i in range(max_retries):
        try:
            res = requests.request(method, url, **kwargs)
            data = res.json()
            if "error" in data:
                err = data["error"]
                # Code 2 is generic transient error, is_transient is a explicit flag
                if err.get("is_transient") or err.get("code") in [1, 2, 10, 368]:
                    print(f"  [RETRY] Meta API transient error (code {err.get('code')}). Attempt {i+1}/{max_retries}. Waiting 10s...")
                    time.sleep(10)
                    continue
            return data
        except Exception as e:
            print(f"  [RETRY] Network or JSON error: {e}. Attempt {i+1}/{max_retries}. Waiting 5s...")
            time.sleep(5)
    
    # Final attempt or error
    return {"error": {"message": f"Max retries ({max_retries}) exceeded or fatal error."}}

def wait_for_container(ig_id, access_token, container_id, timeout=120):
    """Wait for a video container to be ready."""
    url = f"https://graph.facebook.com/v21.0/{container_id}"
    params = {
        "fields": "status_code",
        "access_token": access_token
    }
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        res = request_with_retry("GET", url, params=params)
        status = res.get("status_code")
        if status == "FINISHED":
            return True
        if status == "ERROR":
            print(f"Error: Container processing failed: {res}")
            return False
        print(f"  Container {container_id} status: {status or 'FETCHING'}. Waiting...")
        time.sleep(10)
    
    print("Timeout waiting for container processing.")
    return False

def post_to_instagram(asset_dir: Path, base_url: str):
    ig_id, access_token = get_instagram_config()
    if not ig_id:
        return False

    # Construct the public URLs
    try:
        # Find the path relative to 'docs' directory
        parts = asset_dir.resolve().parts
        if "docs" in parts:
            idx = parts.index("docs")
            rel_parts = parts[idx+1:]
            rel_path = Path(*rel_parts)
        else:
            rel_path = asset_dir.relative_to(os.getcwd())
    except:
        rel_path = asset_dir.name # last resort

    # Normalize slashes for URL
    rel_url_path = "/".join(rel_path.parts)
    full_base_url = f"{base_url}/{rel_url_path}".replace("//", "/").replace("https:/", "https://")

    caption_path = asset_dir / "caption_instagram.txt"
    if not caption_path.exists():
        caption_path = asset_dir / "caption.txt"
    
    if not caption_path.exists():
        print(f"Error: No caption file found in {asset_dir}")
        return False

    with open(caption_path, "r", encoding="utf-8") as f:
        caption = f.read()

    # Find media files
    video_path = next(asset_dir.glob("*.mp4"), None)
    image_names = ["layer.png", "3d_x.png", "3d_y.png"]
    media_urls = []
    
    # Check if images exist and add them
    for name in image_names:
        if (asset_dir / name).exists():
            media_urls.append({"type": "IMAGE", "url": f"{full_base_url}/{name}"})
    
    if video_path:
        media_urls.append({"type": "VIDEO", "url": f"{full_base_url}/{video_path.name}"})

    if not media_urls:
        print("Error: No media files found to post.")
        return False

    try:
        print(f"Creating {len(media_urls)} media containers...")
        item_ids = []
        
        for item in media_urls:
            print(f"  Uploading {item['type']}: {item['url']}")
            api_url = f"https://graph.facebook.com/v21.0/{ig_id}/media"
            payload = {
                "access_token": access_token,
                "is_carousel_item": "true" if len(media_urls) > 1 else "false",
                "caption": caption if len(media_urls) == 1 else "" # Caption goes to parent for carousel
            }
            
            if item["type"] == "IMAGE":
                payload["image_url"] = item["url"]
            else:
                payload["video_url"] = item["url"]
                payload["media_type"] = "VIDEO"

            res = request_with_retry("POST", api_url, data=payload)
            if "id" not in res:
                print(f"Error creating media container: {res}")
                return False
            
            creation_id = res["id"]
            
            # Wait for the container to be processed (important for both image and video)
            if not wait_for_container(ig_id, access_token, creation_id):
                return False
            
            item_ids.append(creation_id)

        # Step 2: Create Carousel Container (if multiple)
        publish_id = None
        if len(item_ids) > 1:
            print("Creating carousel container...")
            api_url = f"https://graph.facebook.com/v21.0/{ig_id}/media"
            payload = {
                "access_token": access_token,
                "media_type": "CAROUSEL",
                "children": ",".join(item_ids),
                "caption": caption
            }
            res = request_with_retry("POST", api_url, data=payload)
            if "id" not in res:
                print(f"Error creating carousel container: {res}")
                return False
            publish_id = res["id"]
        else:
            publish_id = item_ids[0]

        # Step 3: Wait for the FINAL container (carousel or single) to be ready
        print(f"Waiting for final container {publish_id} to be ready...")
        if not wait_for_container(ig_id, access_token, publish_id, timeout=180): # Longer timeout for carousels
            return False

        # Step 4: Publish
        print("Publishing to Instagram...")
        api_url = f"https://graph.facebook.com/v21.0/{ig_id}/media_publish"
        payload = {
            "access_token": access_token,
            "creation_id": publish_id
        }
        res = request_with_retry("POST", api_url, data=payload)
        if "id" not in res:
            print(f"Error during publishing: {res}")
            return False
        
        print(f"Successfully posted to Instagram! Post ID: {res['id']}")
        return True

    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Publish puzzle to Instagram")
    parser.add_argument("--dir", required=True, help="Path to asset directory")
    parser.add_argument("--base-url", required=True, help="Public base URL for assets")
    args = parser.parse_args()

    asset_dir = Path(args.dir)
    if not asset_dir.is_dir():
        print(f"Error: {asset_dir} is not a directory.")
        sys.exit(1)

    post_to_instagram(asset_dir, args.base_url)

if __name__ == "__main__":
    main()
