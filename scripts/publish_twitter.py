#!/usr/bin/env python3
"""
Automatic X (Twitter) post via Playwright (browser automation).

Automates:
  1. Session restore from x_cookies.json
  2. Open X.com compose page
  3. Type tweet text (from caption_twitter.txt)
  4. Attach image (3d_x.png or layer.png)
  5. Click Post button
  6. Confirm success

Usage:
  # Called from auto_publish.py --twitter:
  python scripts/publish_twitter.py \
    --dir docs/images/20260318/005 \
    --url https://souchi-lab.github.io/sochi-blocks/share/20260318_005.html

  # Direct run:
  python scripts/publish_twitter.py --dir docs/images/20260318/005
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
except ImportError:
    print("Error: playwright is not installed.")
    print("  Run: poetry add playwright && poetry run playwright install chromium")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

X_HOME_URL = "https://x.com"
X_COMPOSE_URL = "https://x.com/compose/post"

_LOGIN_CHECK_SELECTORS = [
    '[data-testid="SideNav_AccountSwitcher_Button"]',
    '[data-testid="AppTabBar_Profile_Link"]',
    '[aria-label="Profile"]',
    'a[href="/compose/post"]',
]

_TWEET_TEXT_SELECTORS = [
    '[data-testid="tweetTextarea_0"]',
    '[data-testid="tweetTextarea_0Root"] [contenteditable="true"]',
    '[role="textbox"][aria-label*="Post"]',
    '[role="textbox"][aria-label*="tweet"]',
    '[role="textbox"]',
]

_MEDIA_INPUT_SELECTORS = [
    '[data-testid="fileInput"]',
    'input[type="file"][accept*="image"]',
    'input[type="file"]',
]

_POST_BUTTON_SELECTORS = [
    '[data-testid="tweetButton"]',
    '[data-testid="tweetButtonInline"]',
    'button:has-text("Post")',
    'button:has-text("ポスト")',
]

_SUCCESS_CONTENT_SELECTORS = [
    '[data-testid="toast"]',
    'div:has-text("Your post was sent")',
    'div:has-text("ポストを送信しました")',
]


# ---------------------------------------------------------------------------
# Cookie helpers
# ---------------------------------------------------------------------------

def load_cookies(cookies_path: Path) -> list[dict]:
    """Load X.com cookies from a JSON file (browser extension export format)."""
    if not cookies_path.exists():
        print(f"Error: Cookie file not found: {cookies_path}")
        print()
        print("How to create it:")
        print("  1. Open https://x.com in Chrome and log in manually.")
        print("  2. Install the browser extension 'EditThisCookie' or 'Cookie-Editor'.")
        print("  3. Export cookies as JSON.")
        print(f"  4. Save the file to: {cookies_path}")
        sys.exit(1)

    try:
        raw = json.loads(cookies_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse cookie file: {e}")
        sys.exit(1)

    if not isinstance(raw, list) or len(raw) == 0:
        print(f"Error: Cookie file is empty or not a JSON array: {cookies_path}")
        sys.exit(1)

    cookies = []
    for c in raw:
        if not isinstance(c, dict):
            continue
        name = str(c.get("name", "")).strip()
        value = str(c.get("value", ""))
        domain = str(c.get("domain", ".x.com"))
        path_val = str(c.get("path", "/"))
        if not name or not domain:
            continue
        cookie: dict = {"name": name, "value": value, "domain": domain, "path": path_val}
        if "secure" in c:
            cookie["secure"] = bool(c["secure"])
        if "httpOnly" in c:
            cookie["httpOnly"] = bool(c["httpOnly"])
        same_site = c.get("sameSite")
        if isinstance(same_site, str) and same_site in ("Strict", "Lax", "None"):
            cookie["sameSite"] = same_site
        expiry = c.get("expirationDate") or c.get("expires") or c.get("expiry")
        if isinstance(expiry, (int, float)) and expiry > 0:
            cookie["expires"] = float(expiry)
        cookies.append(cookie)

    print(f"  Loaded {len(cookies)} cookies from {cookies_path.name}")
    return cookies


# ---------------------------------------------------------------------------
# Playwright helpers
# ---------------------------------------------------------------------------

def _find_locator(page, selectors: list[str], label: str, timeout_ms: int = 5000):
    """Try each selector and return the first matching locator, or None."""
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            loc.wait_for(state="attached", timeout=timeout_ms)
            return loc
        except PlaywrightTimeoutError:
            continue
    return None


def _check_login_state(page) -> bool:
    """Return True if the page shows a logged-in X.com session."""
    url = page.url or ""
    if "login" in url or "i/flow" in url:
        return False
    for sel in _LOGIN_CHECK_SELECTORS:
        try:
            page.locator(sel).first.wait_for(state="attached", timeout=5000)
            return True
        except PlaywrightTimeoutError:
            continue
    return False



# ---------------------------------------------------------------------------
# Main publish flow
# ---------------------------------------------------------------------------

def publish_thread_to_x(
    thread_parts: list[dict],
    cookies: list[dict],
) -> bool:
    """
    Post a thread (reply chain) to X.com using post-then-reply approach.

    thread_parts: list of {"caption": str, "image_path": Path | None}
      - parts[0] = main tweet
      - parts[1] = reply to main tweet (e.g. answer image)
      - parts[2] = reply to reply (e.g. URL + CTA)

    Strategy:
      1. Post Part 0 using the standard compose flow.
      2. Get the posted tweet URL via the user's profile.
      3. For each subsequent part: navigate to previous tweet → click Reply
         → type text → attach image → post → get new tweet URL.

    Returns True if all parts posted without fatal errors.
    """
    if not thread_parts:
        print("Error: thread_parts is empty.")
        return False

    # --- Screenshot helper (saved to run-017 dir for debugging) ---
    _ss_dir = Path(__file__).resolve().parent.parent.parent / \
        "ai-problem-solving-framework" / "runs" / \
        "2026-03-18-017_sochi-blocks_x-thread-post-impl"
    _ss_dir.mkdir(parents=True, exist_ok=True)

    def _ss(page, name: str) -> None:
        try:
            page.screenshot(path=str(_ss_dir / f"ss_{name}.png"))
            print(f"  [SS] Saved: ss_{name}.png")
        except Exception as e:
            print(f"  [SS] Failed: {e}")

    # --- Helper: type text into a focused textarea ---
    def _type_into(page, box, caption: str) -> None:
        try:
            box.focus()
        except Exception:
            box.evaluate("el => el.focus()")
        page.wait_for_timeout(300)
        lines = caption.splitlines()
        for li, line in enumerate(lines):
            if line:
                box.press_sequentially(line, delay=20)
            if li < len(lines) - 1:
                page.keyboard.press("Shift+Enter")
            page.wait_for_timeout(50)

    # --- Helper: attach image via file input ---
    def _attach_image(page, image_path: Path) -> None:
        try:
            media_input = _find_locator(page, _MEDIA_INPUT_SELECTORS, "media input", timeout_ms=5000)
            if media_input:
                media_input.set_input_files(str(image_path.resolve()))
                page.wait_for_timeout(3000)
                print(f"  Image attached: {image_path.name}")
            else:
                print(f"  Warning: Could not find media input. Skipping image.")
        except Exception as e:
            print(f"  Warning: Image attach failed: {e}")

    # --- Helper: wait for post button enabled and click ---
    def _click_post(page) -> bool:
        post_btn = _find_locator(page, _POST_BUTTON_SELECTORS, "Post button", timeout_ms=10000)
        if post_btn is None:
            print("  Error: Could not find Post button.")
            return False
        for _ in range(15):
            try:
                if post_btn.is_enabled():
                    break
            except Exception:
                pass
            page.wait_for_timeout(1000)
        try:
            post_btn.dispatch_event("click")
        except Exception:
            post_btn.evaluate("el => el.click()")
        return True

    # --- Helper: wait for navigation away from compose/reply dialog ---
    def _wait_posted(page, url_before: str) -> bool:
        for tick in range(20):
            page.wait_for_timeout(1000)
            current = page.url or ""
            if "compose" not in current and current != url_before:
                print(f"  Navigated → {current[:80]}")
                return True
            for sel in _SUCCESS_CONTENT_SELECTORS:
                try:
                    page.locator(sel).first.wait_for(state="visible", timeout=400)
                    print("  Success toast detected.")
                    return True
                except PlaywrightTimeoutError:
                    pass
            print(f"  Waiting... ({tick + 1}s)")
        return False

    # --- Helper: get latest tweet URL from user profile ---
    def _get_latest_tweet_url(page) -> str | None:
        try:
            profile_loc = page.locator('[data-testid="AppTabBar_Profile_Link"]').first
            profile_href = profile_loc.get_attribute("href", timeout=5000)
            if not profile_href:
                return None
            profile_url = f"{X_HOME_URL}{profile_href}"
            print(f"  Navigating to profile: {profile_url}")
            page.goto(profile_url, wait_until="domcontentloaded", timeout=30000)
            
            # Wait for tweets to render
            try:
                page.locator("article").first.wait_for(state="visible", timeout=10000)
            except Exception:
                print("  Warning: Timeout waiting for articles to render on profile.")

            page.wait_for_timeout(2000)
            
            username = profile_href.strip("/")
            
            # Find first tweet status link belonging to this user
            links = page.locator(f'a[href*="/{username}/status/"]').all()
            for link in links:
                href = link.get_attribute("href") or ""
                if f"/{username}/status/" in href and "analytics" not in href:
                    tweet_url = f"{X_HOME_URL}{href}" if href.startswith("/") else href
                    print(f"  Latest tweet URL: {tweet_url[:80]}")
                    return tweet_url
        except Exception as e:
            print(f"  Warning: Could not get tweet URL: {e}")
        return None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=80)
        context = browser.new_context(viewport={"width": 1280, "height": 900}, locale="en-US")
        print("  Restoring X session from cookies...")
        context.add_cookies(cookies)
        page = context.new_page()

        try:
            # ---------------------------------------------------------------
            # Step 1: Verify session
            # ---------------------------------------------------------------
            print(f"  Opening {X_HOME_URL} ...")
            page.goto(X_HOME_URL, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)

            if not _check_login_state(page):
                print("Error: X session is invalid or expired.")
                _flag = Path(__file__).resolve().parent / "logs" / "twitter_session_error.flag"
                _flag.parent.mkdir(parents=True, exist_ok=True)
                _flag.write_text("session_expired", encoding="utf-8")
                browser.close()
                return False
            print("  Session OK.")
            
            # Clear session error flag if it exists (permanent fix)
            _flag = Path(__file__).resolve().parent / "logs" / "twitter_session_error.flag"
            if _flag.exists():
                try:
                    _flag.unlink()
                except Exception:
                    pass

            # ---------------------------------------------------------------
            # Step 2: Post Part 0 (main tweet) via compose
            # ---------------------------------------------------------------
            part0 = thread_parts[0]
            caption0 = part0.get("caption", "").strip()
            imgs0 = part0.get("image_paths", [])

            print(f"  Opening compose: {X_COMPOSE_URL} ...")
            page.goto(X_COMPOSE_URL, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)

            tweet_box = _find_locator(page, _TWEET_TEXT_SELECTORS, "tweet textbox", timeout_ms=10000)
            if tweet_box is None:
                print("Error: Could not find tweet text area.")
                browser.close()
                return False

            print(f"  Part 0: Entering text ({len(caption0)} chars)...")
            _type_into(page, tweet_box, caption0)
            print("  Part 0: Text entered.")

            for img0 in imgs0:
                if img0.exists():
                    _attach_image(page, img0)
                else:
                    print(f"  Warning: Image not found: {img0}")

            _ss(page, "part0_before_post")

            url_before = page.url or ""
            if not _click_post(page):
                browser.close()
                return False

            if not _wait_posted(page, url_before):
                _ss(page, "part0_timeout")
                print("  WARNING: Could not confirm Part 0 post.")
                browser.close()
                return False

            print("  Part 0 posted.")

            # ---------------------------------------------------------------
            # Step 3: Get the main tweet URL from profile
            # ---------------------------------------------------------------
            page.wait_for_timeout(2000)
            prev_tweet_url = _get_latest_tweet_url(page)
            if not prev_tweet_url:
                print("  Error: Could not find posted tweet URL.")
                browser.close()
                return False

            # ---------------------------------------------------------------
            # Step 4: Post each reply in chain
            # ---------------------------------------------------------------
            _REPLY_BTN_SELECTORS = [
                '[data-testid="reply"]',
            ]
            _REPLY_TEXTAREA_SELECTORS = [
                '[data-testid="tweetTextarea_0"]',
                '[role="textbox"][aria-label*="Reply"]',
                '[role="textbox"]',
            ]

            for i, part in enumerate(thread_parts[1:], start=1):
                caption_i = part.get("caption", "").strip()
                imgs_i = part.get("image_paths", [])

                print(f"  Navigating to tweet for reply {i}: {prev_tweet_url[:80]}")
                page.goto(prev_tweet_url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(3000)
                _ss(page, f"part{i}_before_reply")

                # Click Reply button on the tweet
                reply_btn = _find_locator(page, _REPLY_BTN_SELECTORS, "Reply button", timeout_ms=10000)
                if reply_btn is None:
                    print(f"  Error: Could not find Reply button for part {i}.")
                    _ss(page, f"part{i}_no_reply_btn")
                    browser.close()
                    return False
                try:
                    reply_btn.dispatch_event("click")
                except Exception:
                    reply_btn.evaluate("el => el.click()")
                page.wait_for_timeout(1500)
                print(f"  Part {i}: Reply dialog opened.")

                # Type reply text
                reply_box = _find_locator(page, _REPLY_TEXTAREA_SELECTORS, "reply textarea", timeout_ms=10000)
                if reply_box is None:
                    print(f"  Error: Could not find reply textarea for part {i}.")
                    _ss(page, f"part{i}_no_textarea")
                    browser.close()
                    return False

                if caption_i:
                    print(f"  Part {i}: Entering text ({len(caption_i)} chars)...")
                    _type_into(page, reply_box, caption_i)
                    print(f"  Part {i}: Text entered.")

                for img_i in imgs_i:
                    if img_i.exists():
                        _attach_image(page, img_i)
                    else:
                        print(f"  Warning: Image not found for part {i}: {img_i}")

                _ss(page, f"part{i}_before_post")

                url_before_reply = page.url or ""
                if not _click_post(page):
                    browser.close()
                    return False

                if not _wait_posted(page, url_before_reply):
                    _ss(page, f"part{i}_timeout")
                    print(f"  WARNING: Could not confirm reply {i} post.")
                    browser.close()
                    return False

                print(f"  Part {i} reply posted.")

                # Get the new reply URL for chaining
                page.wait_for_timeout(2000)
                new_url = _get_latest_tweet_url(page)
                if new_url:
                    prev_tweet_url = new_url
                else:
                    print(f"  Warning: Could not get reply {i} URL. Using original tweet for next reply.")

            print(f"  Thread posted successfully ({len(thread_parts)} parts).")
            browser.close()
            return True

        except Exception as e:
            print(f"Unexpected error during X thread post: {e}")
            try:
                _ss(page, "unexpected_error")
            except Exception:
                pass
            browser.close()
            return False


def publish_to_x(
    caption: str,
    cookies: list[dict],
    image_path: Path | None = None,
) -> bool:
    """
    Open X.com compose page and post a tweet with optional image.

    Returns True if the post completed without fatal errors.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=80,
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="en-US",
        )

        print("  Restoring X session from cookies...")
        context.add_cookies(cookies)

        page = context.new_page()

        try:
            # ------------------------------------------------------------------
            # Step 1: Verify session on X home
            # ------------------------------------------------------------------
            print(f"  Opening {X_HOME_URL} ...")
            page.goto(X_HOME_URL, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)

            if not _check_login_state(page):
                print()
                print("Error: X session is invalid or expired.")
                print("  Please refresh your cookies:")
                print("    1. Open https://x.com in Chrome and log in.")
                print("    2. Export cookies via 'EditThisCookie' or 'Cookie-Editor'.")
                print("    3. Overwrite scripts/x_cookies.json")
                print("    4. Re-run this script.")
                _flag = Path(__file__).resolve().parent / "logs" / "twitter_session_error.flag"
                _flag.parent.mkdir(parents=True, exist_ok=True)
                _flag.write_text("session_expired", encoding="utf-8")
                browser.close()
                return False

            print("  Session OK.")

            # Clear session error flag if it exists (permanent fix)
            _flag = Path(__file__).resolve().parent / "logs" / "twitter_session_error.flag"
            if _flag.exists():
                try:
                    _flag.unlink()
                except Exception:
                    pass

            # ------------------------------------------------------------------
            # Step 2: Open compose page
            # ------------------------------------------------------------------
            print(f"  Opening compose: {X_COMPOSE_URL} ...")
            page.goto(X_COMPOSE_URL, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)

            # ------------------------------------------------------------------
            # Step 3: Enter tweet text
            # ------------------------------------------------------------------
            print(f"  Entering tweet ({len(caption)} chars)...")
            tweet_box = _find_locator(page, _TWEET_TEXT_SELECTORS, "tweet textbox", timeout_ms=10000)
            if tweet_box is None:
                print("Error: Could not find tweet text area.")
                print("  Tip: Run 'playwright codegen https://x.com/compose/post' to find current selectors.")
                browser.close()
                return False

            tweet_box.click()
            page.wait_for_timeout(300)
            lines = caption.splitlines()
            for i, line in enumerate(lines):
                if line:
                    tweet_box.press_sequentially(line, delay=20)
                if i < len(lines) - 1:
                    page.keyboard.press("Shift+Enter")
                page.wait_for_timeout(50)
            print("  Tweet text entered.")

            # ------------------------------------------------------------------
            # Step 4: Attach image
            # ------------------------------------------------------------------
            if image_path and image_path.exists():
                print(f"  Attaching image: {image_path.name} ...")
                media_input = _find_locator(page, _MEDIA_INPUT_SELECTORS, "media input", timeout_ms=5000)
                if media_input is None:
                    print("  Warning: Could not find media upload input. Posting without image.")
                    print("  Tip: Run 'playwright codegen https://x.com/compose/post' to update selectors.")
                else:
                    media_input.set_input_files(str(image_path.resolve()))
                    page.wait_for_timeout(3000)  # Wait for image preview to appear
                    print("  Image attached.")
            elif image_path:
                print(f"  Warning: Image not found ({image_path}). Posting without image.")

            # ------------------------------------------------------------------
            # Step 5: Wait for Post button to be enabled, then click
            # ------------------------------------------------------------------
            post_btn = _find_locator(page, _POST_BUTTON_SELECTORS, "Post button", timeout_ms=10000)
            if post_btn is None:
                print("Error: Could not find Post button.")
                browser.close()
                return False

            # Wait for button to be enabled (up to 10s)
            for _ in range(10):
                try:
                    if post_btn.is_enabled():
                        break
                except Exception:
                    pass
                page.wait_for_timeout(1000)
            print("  Post button is ready.")

            print("  Clicking Post button...")
            url_before = page.url or ""
            # X.com has a background overlay div that intercepts pointer events.
            # dispatch_event triggers the React synthetic click event directly on the element,
            # bypassing the overlay without relying on physical mouse coordinates.
            try:
                post_btn.dispatch_event("click")
            except Exception:
                # Fallback: JS evaluate click
                post_btn.evaluate("el => el.click()")

            # ------------------------------------------------------------------
            # Step 6: Confirm post success (up to 15s)
            # ------------------------------------------------------------------
            success = False
            current_url = ""
            for tick in range(15):
                page.wait_for_timeout(1000)
                current_url = page.url or ""

                # Case 1: navigated away from compose page
                if "compose" not in current_url and current_url != url_before:
                    print(f"  [Post] Navigated → {current_url[:80]}")
                    success = True
                    break

                # Case 2: success toast appeared
                for sel in _SUCCESS_CONTENT_SELECTORS:
                    try:
                        page.locator(sel).first.wait_for(state="visible", timeout=500)
                        print("  [Post] Success notification detected.")
                        success = True
                        break
                    except PlaywrightTimeoutError:
                        pass
                if success:
                    break

                print(f"  [Post] Waiting for confirmation... ({tick + 1}s, {current_url[:50]})")

            if not success:
                print("  WARNING: Could not confirm post success after 15s.")
                print(f"           URL: {current_url[:80]}")
                print("           Check X.com profile to confirm if the tweet was posted.")
                _nr_flag = Path(__file__).resolve().parent / "logs" / "twitter_no_confirm.flag"
                _nr_flag.parent.mkdir(parents=True, exist_ok=True)
                _nr_flag.write_text("no_confirm", encoding="utf-8")
                browser.close()
                return False

            print("  Post submitted successfully.")
            browser.close()
            return True

        except Exception as e:
            print(f"Unexpected error during X post flow: {e}")
            browser.close()
            return False


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Automatic X (Twitter) post via Playwright (SoChi BLOCKS)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single post (default)
  python scripts/publish_twitter.py --dir docs/images/20260318/005

  # Thread post: main tweet + reply 2 (answer image) + reply 3 (URL + CTA)
  python scripts/publish_twitter.py --dir docs/images/20260318/005 --thread \\
    --reply "✅ 正解はこちら！" --reply-image docs/images/20260318/005/3d_y.png \\
    --reply "もっと遊ぶ → https://souchi-lab.github.io/sochi-blocks/share/20260318_005.html"
""",
    )
    parser.add_argument("--dir", required=True, help="Image directory (docs/images/YYYYMMDD/NNN)")
    parser.add_argument("--caption", default=None, help="Override caption file path (default: caption_twitter.txt)")
    parser.add_argument("--url", default=None, help="Share URL (for thread reply-3 auto-generation)")
    parser.add_argument("--link-only", action="store_true",
                        help="(legacy flag, ignored) caption_twitter.txt is always used")
    parser.add_argument("--image", default=None, help="Override: path to main tweet image")
    parser.add_argument(
        "--cookies",
        default=None,
        help="Path to X cookies JSON (default: scripts/x_cookies.json)",
    )
    # Thread mode
    parser.add_argument(
        "--thread",
        action="store_true",
        help="Post as a thread (reply chain). Requires at least one --reply.",
    )
    parser.add_argument(
        "--reply",
        action="append",
        dest="replies",
        metavar="TEXT",
        help="Text for each reply in the thread (repeatable, in order).",
    )
    parser.add_argument(
        "--reply-image",
        action="append",
        dest="reply_images",
        metavar="PATH",
        help="Image path for each reply (repeatable, positional — 1st --reply-image goes to 1st --reply).",
    )
    args = parser.parse_args()

    img_dir = Path(args.dir)
    if not img_dir.exists():
        print(f"Error: Directory not found: {img_dir}")
        sys.exit(1)

    # Load main caption
    if args.caption:
        caption_path = Path(args.caption)
    else:
        caption_candidates = [img_dir / "caption_twitter.txt", img_dir / "caption.txt"]
        caption_path = next((p for p in caption_candidates if p.exists()), None)
    if caption_path is None:
        print(f"Error: No caption file found in {img_dir}")
        sys.exit(1)
    caption = caption_path.read_text(encoding="utf-8").strip()
    if not caption:
        print("Error: Caption file is empty.")
        sys.exit(1)

    # Resolve main image
    if args.image:
        image_path = Path(args.image)
    else:
        image_candidates = [img_dir / "layer.png", img_dir / "3d_x.png"]
        image_path = next((p for p in image_candidates if p.exists()), None)

    # Resolve cookies
    cookies_path = Path(args.cookies) if args.cookies else Path(__file__).resolve().parent / "x_cookies.json"
    cookies = load_cookies(cookies_path)

    # ------------------------------------------------------------------
    # Thread mode
    # ------------------------------------------------------------------
    if args.thread:
        replies = args.replies or []
        if not replies:
            print("Error: --thread requires at least one --reply TEXT.")
            sys.exit(1)

        # --reply-image supports colon-separated multiple paths: "3d_x.png:3d_y.png"
        reply_images: list[list[Path]] = []
        for rimg in (args.reply_images or []):
            paths = [Path(p) for p in rimg.split(":") if p]
            reply_images.append([p for p in paths if p.exists()])
        # Pad to len(replies) with empty list
        while len(reply_images) < len(replies):
            reply_images.append([])

        thread_parts: list[dict] = [{"caption": caption, "image_paths": [image_path] if image_path else []}]
        for txt, imgs in zip(replies, reply_images):
            thread_parts.append({"caption": txt.strip(), "image_paths": imgs})

        print()
        print(f"  Dir:       {img_dir}")
        print(f"  Caption:   {caption_path.name} ({len(caption)} chars)")
        print(f"  Main img:  {image_path.name if image_path else '(none)'}")
        print(f"  Replies:   {len(replies)}")
        for i, (txt, imgs) in enumerate(zip(replies, reply_images), start=1):
            img_names = "+".join(p.name for p in imgs) if imgs else "(none)"
            print(f"    Reply {i}: {txt[:60]!r}  img={img_names}")
        print(f"  Cookies:   {cookies_path.name} ({len(cookies)} cookies)")
        print()

        success = publish_thread_to_x(thread_parts, cookies)
        sys.exit(0 if success else 1)

    # ------------------------------------------------------------------
    # Single post mode (default)
    # ------------------------------------------------------------------
    print()
    print(f"  Dir:     {img_dir}")
    print(f"  Caption: {caption_path.name} ({len(caption)} chars)")
    print(f"  Image:   {image_path.name if image_path else '(none)'}")
    print(f"  Cookies: {cookies_path.name} ({len(cookies)} cookies)")
    print()

    success = publish_to_x(caption, cookies, image_path=image_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
