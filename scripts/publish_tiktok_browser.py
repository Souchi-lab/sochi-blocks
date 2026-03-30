#!/usr/bin/env python3
# Force UTF-8 output on Windows (avoids cp932 crash with em dash etc.)
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
"""
Semi-automatic TikTok video post via Playwright (browser automation).

Automates:
  1. Session restore from cookies JSON
  2. Open TikTok upload page
  3. Upload video file
  4. Wait for encoding
  5. Enter caption
  6. Wait for Post button to be clickable
  7. Hand off to user (or auto-click with --auto)

Usage:
  # Semi-auto (user clicks Post manually)
  python scripts/publish_tiktok_browser.py \
    --video docs/sns_videos/20260312_007_full.mp4 \
    --caption docs/images/20260312/007/caption.txt

  # Future: auto-click Post
  python scripts/publish_tiktok_browser.py \
    --video docs/sns_videos/20260312_007_full.mp4 \
    --caption docs/images/20260312/007/caption.txt \
    --auto
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

TIKTOK_UPLOAD_URL = "https://www.tiktok.com/upload"
CAPTION_MAX_LENGTH = 2200   # TikTok caption character limit
ENCODING_TIMEOUT_S = 120    # Max seconds to wait for TikTok video encoding
POST_READY_TIMEOUT_S = 60   # Max seconds to wait for Post button to be enabled

# Selector candidates in priority order.
# TikTok uses data-e2e attributes which are relatively stable,
# but UI updates will occasionally break them.
# If selectors stop working, run:  playwright codegen https://www.tiktok.com/upload

_FILE_INPUT_SELECTORS = [
    'input[type="file"][accept*="video"]',
    'input[type="file"]',
]

_CAPTION_SELECTORS = [
    '[data-e2e="caption-editor"]',
    '.DraftEditor-root [contenteditable="true"]',
    '[contenteditable="true"]',
]

_POST_BUTTON_SELECTORS = [
    '[data-e2e="post_video_button"]',
    'button:has-text("Post")',
    'button:has-text("投稿")',
]

_COVER_BUTTON_SELECTORS = [
    # Current TikTok Studio UI (2026): "Edit cover" div inside cover_container
    '[data-e2e="cover_container"] .edit-container',
    '.edit-container',
    'div:has-text("Edit cover")',
    '[data-e2e="cover_container"]',
    # Legacy selectors (kept as fallback)
    '[data-e2e="cover-change-btn"]',
    '[data-e2e="select-cover"]',
    'button:has-text("Select cover")',
    'button:has-text("カバーを選択")',
]

_COVER_UPLOAD_SELECTORS = [
    'input[type="file"][accept*="image"]',
    '[data-e2e="cover-upload-input"]',
]

_COVER_CONFIRM_SELECTORS = [
    '[data-e2e="cover-confirm-btn"]',
    'button:has-text("Confirm")',
    'button:has-text("確認")',
    'button:has-text("完了")',
]


# ---------------------------------------------------------------------------
# Caption helpers
# ---------------------------------------------------------------------------

def prepare_caption(caption_path: Path) -> str:
    """
    Load caption text from file and validate for TikTok.

    Extend this function for TikTok-specific formatting
    (e.g. truncation, hashtag normalization) when needed.
    """
    if not caption_path.exists():
        print(f"Error: Caption file not found: {caption_path}")
        sys.exit(1)

    text = caption_path.read_text(encoding="utf-8").strip()
    if not text:
        print("Warning: Caption file is empty. Proceeding with no caption.")
        return ""

    if len(text) > CAPTION_MAX_LENGTH:
        print(
            f"Warning: Caption is {len(text)} chars, exceeds TikTok limit ({CAPTION_MAX_LENGTH}). "
            "TikTok may truncate it."
        )

    return text


# ---------------------------------------------------------------------------
# Cookie helpers
# ---------------------------------------------------------------------------

def load_cookies(cookies_path: Path) -> list[dict]:
    """
    Load TikTok cookies from a JSON file (browser extension export format).

    Supported export formats:
      - EditThisCookie  (Chrome extension)
      - Cookie-Editor   (Chrome/Firefox extension)
    Both export a JSON array of cookie objects.
    """
    if not cookies_path.exists():
        print(f"Error: Cookie file not found: {cookies_path}")
        print()
        print("How to create it:")
        print("  1. Open https://www.tiktok.com in Chrome and log in manually.")
        print("  2. Install the browser extension 'EditThisCookie' or 'Cookie-Editor'.")
        print("  3. Export cookies as JSON.")
        print(f"  4. Save the file to: {cookies_path}")
        print()
        sys.exit(1)

    try:
        raw = json.loads(cookies_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse cookie file ({cookies_path}): {e}")
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
        domain = str(c.get("domain", ".tiktok.com"))
        path = str(c.get("path", "/"))

        if not name or not domain:
            continue

        cookie: dict = {
            "name": name,
            "value": value,
            "domain": domain,
            "path": path,
        }

        # Optional fields (Playwright accepts these)
        if "secure" in c:
            cookie["secure"] = bool(c["secure"])
        if "httpOnly" in c:
            cookie["httpOnly"] = bool(c["httpOnly"])
        same_site = c.get("sameSite")
        if isinstance(same_site, str) and same_site in ("Strict", "Lax", "None"):
            cookie["sameSite"] = same_site

        # Expiry: browser extensions use "expirationDate", Playwright uses "expires"
        expiry = c.get("expirationDate") or c.get("expires") or c.get("expiry")
        if isinstance(expiry, (int, float)) and expiry > 0:
            cookie["expires"] = float(expiry)

        cookies.append(cookie)

    print(f"  Loaded {len(cookies)} cookies from {cookies_path.name}")
    return cookies


# ---------------------------------------------------------------------------
# Playwright frame helpers
# ---------------------------------------------------------------------------

def _get_frames(page) -> list:
    """
    Return candidate frames to search for the upload UI.

    TikTok may embed the upload form inside an iframe.
    Returns [main_frame, ...tiktok_iframes] so callers can try each.
    """
    frames = [page.main_frame]
    for frame in page.frames:
        if frame == page.main_frame:
            continue
        if "tiktok.com" in (frame.url or ""):
            frames.append(frame)
    return frames


def _find_locator_in_frames(page, selectors: list[str], label: str, timeout_ms: int = 5000):
    """
    Search across all frames for the first selector that matches.

    Returns (frame, locator) or (None, None) if not found.
    """
    for frame in _get_frames(page):
        for sel in selectors:
            try:
                loc = frame.locator(sel).first
                loc.wait_for(state="attached", timeout=timeout_ms)
                return frame, loc
            except PlaywrightTimeoutError:
                continue
    return None, None


def _dismiss_joyride_overlay(page) -> None:
    """
    Dismiss TikTok's react-joyride guided tour overlay if present.

    TikTok occasionally shows a guided tour that places a full-screen overlay
    (data-test-id="overlay") which intercepts all pointer events and blocks
    interaction with the caption editor and Post button.

    Strategy:
      1. Try clicking a Skip / Close button on the tour tooltip.
      2. Fallback: press Escape.
      3. Fallback: JavaScript click on the overlay element directly.
    Does nothing (silently) if the overlay is not present.
    """
    _SKIP_SELECTORS = [
        '[data-test-id="button-skip"]',
        'button:has-text("Skip")',
        'button:has-text("スキップ")',
        '[aria-label="Close"]',
        '[data-testid="joyride-close"]',
    ]
    _OVERLAY_SELECTORS = [
        '[data-test-id="overlay"]',
        '.react-joyride__overlay',
    ]

    # Check if overlay is present at all (fast check, 1s timeout)
    overlay_present = False
    for sel in _OVERLAY_SELECTORS:
        try:
            page.locator(sel).first.wait_for(state="visible", timeout=1000)
            overlay_present = True
            break
        except PlaywrightTimeoutError:
            continue
    if not overlay_present:
        return

    print("  [Overlay] TikTok guided tour detected. Attempting to dismiss...")

    # 1. Try skip/close button
    for sel in _SKIP_SELECTORS:
        try:
            btn = page.locator(sel).first
            btn.wait_for(state="visible", timeout=2000)
            btn.click()
            page.wait_for_timeout(800)
            print(f"  [Overlay] Dismissed via '{sel}'.")
            return
        except PlaywrightTimeoutError:
            continue

    # 2. Fallback: Escape key
    try:
        page.keyboard.press("Escape")
        page.wait_for_timeout(800)
        print("  [Overlay] Dismissed via Escape key.")
        return
    except Exception:
        pass

    # 3. Fallback: JavaScript click on the overlay to dismiss
    try:
        page.evaluate("""
            const overlay = document.querySelector('[data-test-id="overlay"]')
                         || document.querySelector('.react-joyride__overlay');
            if (overlay) overlay.click();
        """)
        page.wait_for_timeout(800)
        print("  [Overlay] Dismissed via JavaScript click.")
    except Exception as e:
        print(f"  [Overlay] Could not dismiss overlay: {e}")
        print("  [Overlay] Interactions may fail. Check the browser window.")


def _check_login_state(page) -> bool:
    """Return False if TikTok redirected to a login page."""
    url = page.url or ""
    if "login" in url or "signin" in url:
        return False
    # The upload page renders the file-drop area if logged in
    try:
        _, loc = _find_locator_in_frames(page, _FILE_INPUT_SELECTORS, "file input", timeout_ms=10000)
        return loc is not None
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Upload flow
# ---------------------------------------------------------------------------

def _upload_video(page, video_path: Path) -> bool:
    """Submit the video file to TikTok's hidden file input."""
    print(f"  Uploading video: {video_path.name}")

    frame, file_input = _find_locator_in_frames(
        page, _FILE_INPUT_SELECTORS, "file input", timeout_ms=15000
    )
    if file_input is None:
        print("Error: Could not find the file upload input on the page.")
        print("       TikTok's UI may have changed.")
        print("  Tip: Run 'playwright codegen https://www.tiktok.com/upload' to find the current selector.")
        return False

    file_input.set_input_files(str(video_path.resolve()))
    print("  File submitted.")
    return True


def _wait_for_encoding(page) -> tuple:
    """
    Poll until the caption editor appears, which signals encoding is done.

    Returns (frame, caption_locator) or (None, None) on timeout.
    """
    print(f"  Waiting for TikTok to process the video (up to {ENCODING_TIMEOUT_S}s)...")

    interval_ms = 4000
    iterations = (ENCODING_TIMEOUT_S * 1000) // interval_ms

    for i in range(iterations):
        page.wait_for_timeout(interval_ms)

        # Check for upload-error indicators first
        for frame in _get_frames(page):
            for err_sel in [
                '[data-e2e="upload-error"]',
                'div:has-text("Upload failed")',
                'div:has-text("アップロードに失敗")',
            ]:
                try:
                    frame.locator(err_sel).wait_for(state="visible", timeout=500)
                    print("Error: TikTok reported an upload error. Check the browser window.")
                    return None, None
                except PlaywrightTimeoutError:
                    pass

        frame, caption_loc = _find_locator_in_frames(
            page, _CAPTION_SELECTORS, "caption editor", timeout_ms=2000
        )
        if caption_loc is not None:
            elapsed = (i + 1) * (interval_ms // 1000)
            print(f"  Caption editor appeared (~{elapsed}s).")
            return frame, caption_loc

        elapsed = (i + 1) * (interval_ms // 1000)
        print(f"  Still processing... ({elapsed}s elapsed)")

    print(f"Error: Timed out waiting for video encoding ({ENCODING_TIMEOUT_S}s).")
    print("  Possible causes:")
    print("    - Video is too large or in an unsupported format")
    print("    - Slow network")
    print("    - TikTok UI changed (caption editor selector mismatch)")
    print("  Tip: Run 'playwright codegen https://www.tiktok.com/upload' to update selectors.")
    return None, None


def _enter_caption(page, frame, caption_loc, caption: str) -> None:
    """Type the caption into TikTok's contenteditable editor."""
    if not caption:
        return

    print(f"  Entering caption ({len(caption)} chars)...")
    try:
        caption_loc.click()
        page.wait_for_timeout(400)

        # Select all and delete any placeholder text
        page.keyboard.press("Control+a")
        page.wait_for_timeout(200)

        # Type line-by-line to preserve newlines.
        # Use press_sequentially (sends individual key events) for contenteditable.
        lines = caption.splitlines()
        for i, line in enumerate(lines):
            if line:
                caption_loc.press_sequentially(line, delay=25)
            if i < len(lines) - 1:
                # Shift+Enter inserts a line break inside the editor
                page.keyboard.press("Shift+Enter")
            page.wait_for_timeout(80)

        # Dismiss hashtag autocomplete dropdown if it opened
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
        print("  Caption entered.")

    except Exception as e:
        print(f"Warning: Caption input encountered an issue: {e}")
        print("  You can type the caption manually in the browser window.")


def _set_cover(page, cover_path: Path) -> bool:
    """
    Open TikTok's cover selection UI and upload a custom cover image.

    Returns True if successful, False if the UI could not be found
    (non-fatal — caller should warn and continue without cover).
    """
    print(f"  Setting cover image: {cover_path.name}")

    # Find "Select cover" button
    _, cover_btn = _find_locator_in_frames(
        page, _COVER_BUTTON_SELECTORS, "cover button", timeout_ms=8000
    )
    if cover_btn is None:
        print("Warning: Could not find 'Select cover' button. Skipping cover upload.")
        print("  You can set the cover manually in the browser window.")
        return False

    try:
        cover_btn.dispatch_event("click")
        page.wait_for_timeout(1500)
    except Exception:
        try:
            cover_btn.click(force=True)
            page.wait_for_timeout(1500)
        except Exception as e:
            print(f"Warning: Failed to click cover button: {e}")
            return False


    # Click "Upload cover" tab in the cover dialog (TikTok default is "Select cover").
    # The tab text is "Upload cover" (not "Upload"), and it is a div/span, not a button.
    _UPLOAD_TAB_SELECTORS = [
        'text=Upload cover',
        ':text-is("Upload cover")',
        'div:has-text("Upload cover")',
        'span:has-text("Upload cover")',
    ]
    _, upload_tab = _find_locator_in_frames(
        page, _UPLOAD_TAB_SELECTORS, "upload tab", timeout_ms=5000
    )
    if upload_tab is not None:
        try:
            upload_tab.click()
            page.wait_for_timeout(1000)
            print("  Switched to Upload cover tab.")
        except Exception as e:
            print(f"  Warning: Could not click Upload cover tab: {e}")
    else:
        print("  Warning: Upload cover tab not found — trying direct file upload.")

    # Find image upload input inside the cover dialog
    _, upload_input = _find_locator_in_frames(
        page, _COVER_UPLOAD_SELECTORS, "cover upload input", timeout_ms=8000
    )
    if upload_input is None:
        print("Warning: Could not find cover image upload input. Skipping cover upload.")
        return False

    try:
        upload_input.set_input_files(str(cover_path.resolve()))
        page.wait_for_timeout(3000)
        print(f"  Cover image uploaded: {cover_path.name}")
    except Exception as e:
        print(f"Warning: Failed to upload cover image: {e}")
        return False

    # Confirm / close the cover dialog.
    # Wait up to 15s for TikTok to process the uploaded image and enable Confirm.
    _, confirm_btn = _find_locator_in_frames(
        page, _COVER_CONFIRM_SELECTORS, "cover confirm", timeout_ms=8000
    )
    if confirm_btn is None:
        print("Warning: Could not find confirm button. Please confirm cover manually.")
        return False

    for tick in range(15):
        try:
            if confirm_btn.is_enabled():
                break
        except Exception:
            pass
        print(f"  Waiting for Confirm button to be enabled... ({tick + 1}s)")
        page.wait_for_timeout(1000)

    try:
        # TikTok has a hidden Confirm button (positioned at ~-99999px) in addition to
        # the visible one. Standard locators find the hidden one first.
        # Use JS to find the VISIBLE Confirm button (getBoundingClientRect x/y > 0)
        # and fire a full mouse event sequence required by TikTok's React handlers.
        result = page.evaluate("""
            () => {
                const btns = Array.from(document.querySelectorAll('button'));
                const btn = btns.find(b => {
                    const t = (b.textContent || '').trim();
                    if (t !== 'Confirm') return false;
                    const r = b.getBoundingClientRect();
                    return r.width > 0 && r.x > -100 && r.y > -100 && r.x < 2000;
                });
                if (!btn) return null;
                const r = btn.getBoundingClientRect();
                const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
                const opts = {bubbles: true, cancelable: true, clientX: cx, clientY: cy};
                btn.dispatchEvent(new MouseEvent('mouseover', opts));
                btn.dispatchEvent(new MouseEvent('mousedown', opts));
                btn.dispatchEvent(new MouseEvent('mouseup',   opts));
                btn.dispatchEvent(new MouseEvent('click',     opts));
                return {x: cx, y: cy, w: r.width};
            }
        """)
        if result:
            print(f"  Confirm clicked at ({result['x']:.0f}, {result['y']:.0f})")
        else:
            print("  Warning: visible Confirm button not found via JS")
        page.wait_for_timeout(2000)
        print("  Cover confirmed.")
    except Exception as e:
        print(f"Warning: Could not click confirm button: {e}")

    # If modal is still open (e.g. confirm failed), close it with Escape
    # so the TUXModal-overlay doesn't block the Post button.
    try:
        page.locator('.TUXModal-overlay').first.wait_for(state="visible", timeout=1000)
        print("  Warning: Cover modal still open — dismissing with Escape.")
        page.keyboard.press("Escape")
        page.wait_for_timeout(1000)
    except PlaywrightTimeoutError:
        pass  # Modal already closed — good

    return True


def _wait_for_post_button(page, frame) -> object | None:
    """
    Locate and wait for the Post button.

    semi-auto:
      - visible になればOK（手動で押すので enabled までは必須にしない）
    auto:
      - visible の後、enabled になるまで待つ

    Returns the locator if found, None otherwise.
    """
    print(f"  Waiting for Post button to be ready (up to {POST_READY_TIMEOUT_S}s)...")

    post_frame, post_btn = _find_locator_in_frames(
        page, _POST_BUTTON_SELECTORS, "Post button", timeout_ms=10000
    )
    if post_btn is None:
        print("Warning: Could not locate the Post button.")
        print("         Check the browser window — you may need to scroll down.")
        return None

    # まずは visible まで待つ
    try:
        post_btn.wait_for(state="visible", timeout=10000)
        print("  Post button is visible.")
    except PlaywrightTimeoutError:
        print("Warning: Post button was found but did not become visible.")
        return post_btn

    # enabled になるまでポーリング
    interval_ms = 2000
    iterations = (POST_READY_TIMEOUT_S * 1000) // interval_ms

    for i in range(iterations):
        try:
            enabled = post_btn.is_enabled()
            disabled_attr = post_btn.get_attribute("disabled")
            aria_disabled = post_btn.get_attribute("aria-disabled")

            if enabled and disabled_attr is None and aria_disabled not in ("true", "True"):
                print("  Post button is enabled.")
                return post_btn

            elapsed = (i + 1) * (interval_ms // 1000)
            print(
                f"  Waiting for enablement... ({elapsed}s elapsed, "
                f"is_enabled={enabled}, disabled={disabled_attr}, aria-disabled={aria_disabled})"
            )
        except Exception as e:
            print(f"  Waiting for enablement... locator check failed: {e}")

        page.wait_for_timeout(interval_ms)

    print("Warning: Post button did not become enabled after waiting.")
    print("         It may require adjusting privacy settings, dismissing a dialog, or scrolling down.")
    return post_btn


# ---------------------------------------------------------------------------
# Main publish flow
# ---------------------------------------------------------------------------

def publish_to_tiktok(
    video_path: Path,
    caption: str,
    cookies: list[dict],
    auto: bool,
    cover_path: Path | None = None,
) -> bool:
    """
    Open TikTok upload page and prepare a post.

    Semi-auto (default): stops before clicking Post, waits for user.
    Auto (--auto):       clicks Post automatically.

    Returns True if the flow completed without fatal errors.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=80,  # Slight slowdown helps avoid bot detection
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="en-US",
        )

        # Restore TikTok session
        print("  Restoring TikTok session from cookies...")
        context.add_cookies(cookies)

        page = context.new_page()

        try:
            # ------------------------------------------------------------------
            # Step 1: Open upload page
            # ------------------------------------------------------------------
            print(f"  Opening {TIKTOK_UPLOAD_URL} ...")
            page.goto(TIKTOK_UPLOAD_URL, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)  # Let JS settle

            if not _check_login_state(page):
                print()
                print("Error: TikTok session is invalid or expired.")
                print("  Please refresh your cookies:")
                print("    1. Open https://www.tiktok.com in Chrome and log in.")
                print("    2. Export cookies via 'EditThisCookie' or 'Cookie-Editor'.")
                print("    3. Overwrite scripts/tiktok_cookies.json")
                print("    4. Re-run this script.")
                # Write flag file so auto_publish.py can log session_expired to hook_log.csv
                _flag = Path(__file__).resolve().parent / "logs" / "tiktok_session_error.flag"
                _flag.parent.mkdir(parents=True, exist_ok=True)
                _flag.write_text("session_expired", encoding="utf-8")
                browser.close()
                return False

            print("  Session OK.")

            # Clear session error flag if it exists (permanent fix)
            _flag = Path(__file__).resolve().parent / "logs" / "tiktok_session_error.flag"
            if _flag.exists():
                try:
                    _flag.unlink()
                except Exception:
                    pass

            # ------------------------------------------------------------------
            # Step 2: Upload video
            # ------------------------------------------------------------------
            if not _upload_video(page, video_path):
                browser.close()
                return False

            # ------------------------------------------------------------------
            # Step 3: Wait for encoding
            # ------------------------------------------------------------------
            frame, caption_loc = _wait_for_encoding(page)
            if caption_loc is None:
                browser.close()
                return False

            # ------------------------------------------------------------------
            # Step 3.5: Dismiss guided tour overlay (if present)
            # ------------------------------------------------------------------
            _dismiss_joyride_overlay(page)

            # ------------------------------------------------------------------
            # Step 4: Enter caption
            # ------------------------------------------------------------------
            _enter_caption(page, frame, caption_loc, caption)

            # ------------------------------------------------------------------
            # Step 4.5: Set cover image (if provided)
            # ------------------------------------------------------------------
            if cover_path and cover_path.exists():
                _set_cover(page, cover_path)
            elif cover_path:
                print(f"  Warning: Cover image not found: {cover_path}")

            # ------------------------------------------------------------------
            # Step 5: Wait for Post button
            # ------------------------------------------------------------------
            post_btn = _wait_for_post_button(page, frame)

            # ------------------------------------------------------------------
            # Step 6: Semi-auto handoff  OR  auto-click
            # ------------------------------------------------------------------
            if auto:
                # --auto: click Post automatically
                if post_btn is None:
                    print("Error: --auto requested but Post button could not be found.")
                    browser.close()
                    return False

                print()
                print("  [--auto] Clicking Post button...")
                # Use same JS approach as Confirm: find visible button by getBoundingClientRect
                # and fire full mouse event sequence.
                post_result = page.evaluate("""
                    () => {
                        const btns = Array.from(document.querySelectorAll('[data-e2e="post_video_button"], button'));
                        const btn = btns.find(b => {
                            const e2e = b.getAttribute('data-e2e');
                            if (e2e && e2e !== 'post_video_button') return false;
                            const t = (b.textContent || '').trim();
                            if (!e2e && t !== 'Post' && t !== '投稿') return false;
                            const r = b.getBoundingClientRect();
                            return r.width > 0 && r.x > -100 && r.y > -100 && r.x < 2000;
                        });
                        if (!btn) return null;
                        const r = btn.getBoundingClientRect();
                        const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
                        const opts = {bubbles: true, cancelable: true, clientX: cx, clientY: cy};
                        btn.dispatchEvent(new MouseEvent('mouseover', opts));
                        btn.dispatchEvent(new MouseEvent('mousedown', opts));
                        btn.dispatchEvent(new MouseEvent('mouseup',   opts));
                        btn.dispatchEvent(new MouseEvent('click',     opts));
                        return {x: cx, y: cy};
                    }
                """)
                if post_result:
                    print(f"  [--auto] Post button clicked at ({post_result['x']:.0f}, {post_result['y']:.0f})")
                else:
                    print("  [--auto] Warning: visible Post button not found via JS, fallback dispatch_event")
                    post_btn.dispatch_event("click")

                # Detect post success (up to 15s).
                # TikTok typically stays on tiktokstudio/upload but shows a review/success
                # message after submission. Also handle redirect to a non-upload page.
                # Known upload-page patterns (still filling the form = not yet submitted):
                #   https://www.tiktok.com/upload  (legacy)
                # Success destination (also an /upload path but shows review content):
                #   https://www.tiktok.com/tiktokstudio/upload  → DO NOT flag as failure
                _STILL_UPLOADING_PATTERNS = ["www.tiktok.com/upload"]  # legacy upload only
                _SUCCESS_CONTENT_SELECTORS = [
                    'div:has-text("Content under review")',
                    'div:has-text("コンテンツの審査")',
                    'div:has-text("under review")',
                    '[data-e2e="post-success"]',
                    '[data-e2e="upload-success"]',
                ]
                # "Continue to post?" dialog selectors (copyright check still in progress)
                _POST_NOW_SELECTORS = [
                    'button:has-text("Post now")',
                    'button:has-text("今すぐ投稿")',
                ]

                success = False
                current_url = ""
                for tick in range(20):
                    page.wait_for_timeout(1000)
                    current_url = page.url or ""

                    # Case 0: "Continue to post?" dialog — click "Post now"
                    for sel in _POST_NOW_SELECTORS:
                        try:
                            post_now = page.locator(sel).first
                            post_now.wait_for(state="visible", timeout=500)
                            print(f"  [--auto] 'Continue to post?' dialog — clicking Post now.")
                            post_now.evaluate("el => el.click()")
                            page.wait_for_timeout(1000)
                            break
                        except PlaywrightTimeoutError:
                            pass

                    # Case 1: redirected away from upload entirely
                    if not any(p in current_url for p in ["tiktok.com/upload", "tiktokstudio/upload"]):
                        print(f"  [--auto] Redirected → {current_url[:80]}")
                        success = True
                        break
                    # Case 2: still on tiktokstudio/upload but success content appeared
                    for sel in _SUCCESS_CONTENT_SELECTORS:
                        try:
                            page.locator(sel).first.wait_for(state="visible", timeout=500)
                            print(f"  [--auto] Post accepted (review/success content detected).")
                            success = True
                            break
                        except PlaywrightTimeoutError:
                            pass
                    if success:
                        break
                    print(f"  [--auto] Waiting for post confirmation... ({tick + 1}s)")

                if not success:
                    print("  [--auto] WARNING: Could not confirm post success after 20s.")
                    print(f"           URL: {current_url[:80]}")
                    print("           Check TikTok Studio to confirm if the video was posted.")
                    _nr_flag = Path(__file__).resolve().parent / "logs" / "tiktok_no_redirect.flag"
                    _nr_flag.parent.mkdir(parents=True, exist_ok=True)
                    _nr_flag.write_text("no_redirect", encoding="utf-8")
                    browser.close()
                    return False
                print("  [--auto] Post submitted successfully.")

            else:
                # Semi-auto: hand off to the user
                print()
                print("=" * 60)
                print("  Ready to post!")
                print()
                print("  The browser is open. Please:")
                print("    1. Review the video preview and caption.")
                if cover_path and cover_path.exists():
                    print(f"    2. Set cover image manually → use: {cover_path.name}")
                print("    3. Adjust privacy / settings if needed.")
                print("    4. Click the [Post] button to publish.")
                print()
                print("  Press Enter here when you are done (or to cancel).")
                print("=" * 60)
                input()
                print("  Browser closed.")

            browser.close()
            return True

        except Exception as e:
            print(f"Unexpected error during TikTok post flow: {e}")
            browser.close()
            return False


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _resolve_paths_from_puzzle_id(puzzle_id: str) -> tuple[Path, Path, Path]:
    """
    Derive video / caption / cover paths from a puzzle_id like '20260313_001'.

    Returns (video_path, caption_path, cover_path).
    """
    # Normalize: accept both '20260313_001' and '20260313001'
    if "_" not in puzzle_id and len(puzzle_id) == 11:
        puzzle_id = puzzle_id[:8] + "_" + puzzle_id[8:]

    date_part, num_part = puzzle_id.split("_")
    asset_dir = PROJECT_ROOT / "docs" / "images" / date_part / num_part

    video_candidates = [
        PROJECT_ROOT / "docs" / "sns_videos" / f"{puzzle_id}_tiktok.mp4",
        PROJECT_ROOT / "docs" / "sns_videos" / f"{puzzle_id}_full.mp4",
    ]
    video_path = next((p for p in video_candidates if p.exists()), video_candidates[0])
    caption_path = asset_dir / "caption_tiktok.txt"
    cover_path = asset_dir / "3d_x.png"

    return video_path, caption_path, cover_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Semi-automatic TikTok post via Playwright (SoChi BLOCKS)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Specify puzzle ID only (paths are auto-resolved)
  python scripts/publish_tiktok_browser.py --puzzle-id 20260313_001

  # Auto-click Post (use with caution)
  python scripts/publish_tiktok_browser.py --puzzle-id 20260313_001 --auto
""",
    )
    parser.add_argument("--puzzle-id", default=None, help="Puzzle ID (e.g. 20260313_001)")
    parser.add_argument("--video", default=None, help="Override: path to video file (.mp4)")
    parser.add_argument("--caption", default=None, help="Override: path to caption text file")
    parser.add_argument("--cover", default=None, help="Override: path to cover image file")
    parser.add_argument(
        "--cookies",
        default=None,
        help="Path to TikTok cookies JSON (default: scripts/tiktok_cookies.json)",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Automatically click the Post button without manual confirmation",
    )
    args = parser.parse_args()

    if not args.puzzle_id and not args.video:
        parser.error("Either --puzzle-id or --video is required.")

    # --- Resolve paths ---
    if args.puzzle_id:
        video_path, caption_path, cover_path = _resolve_paths_from_puzzle_id(args.puzzle_id)
        # Allow individual overrides
        if args.video:
            video_path = Path(args.video)
        if args.caption:
            caption_path = Path(args.caption)
        if args.cover:
            cover_path = Path(args.cover)
    else:
        video_path = Path(args.video)
        caption_path = Path(args.caption) if args.caption else None
        cover_path = Path(args.cover) if args.cover else None

    if not video_path.exists():
        print(f"Error: Video file not found: {video_path}")
        sys.exit(1)

    if args.cookies:
        cookies_path = Path(args.cookies)
    else:
        cookies_path = Path(__file__).resolve().parent / "tiktok_cookies.json"

    # --- Warn on --auto ---
    if args.auto:
        print("Warning: --auto mode will click the Post button automatically.")
        print("         Ensure the video and caption are correct before proceeding.")
        print()

    # --- Load inputs ---
    caption = prepare_caption(caption_path) if caption_path else ""
    cookies = load_cookies(cookies_path)

    print()
    print(f"  Video:   {video_path}")
    print(f"  Caption: {caption_path} ({len(caption)} chars)")
    print(f"  Cover:   {cover_path if cover_path else '(none)'}")
    print(f"  Cookies: {cookies_path} ({len(cookies)} cookies)")
    print(f"  Mode:    {'auto' if args.auto else 'semi-auto (manual Post click)'}")
    print()

    success = publish_to_tiktok(video_path, caption, cookies, auto=args.auto, cover_path=cover_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
