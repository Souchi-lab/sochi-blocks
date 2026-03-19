import json, sys
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

COOKIES_PATH = Path(__file__).parent / "tiktok_cookies.json"
VIDEO_PATH = Path(__file__).parent.parent / "docs" / "sns_videos" / "20260318_008_tiktok.mp4"
COVER_PATH = Path(__file__).parent.parent / "docs" / "images" / "20260318" / "008" / "3d_x.png"

cookies = json.loads(COOKIES_PATH.read_text(encoding="utf-8"))
clean = []
for c in cookies:
    ck = {"name": str(c.get("name","")), "value": str(c.get("value","")),
          "domain": str(c.get("domain",".tiktok.com")), "path": str(c.get("path","/"))}
    exp = c.get("expirationDate") or c.get("expires")
    if isinstance(exp, (int,float)) and exp > 0:
        ck["expires"] = float(exp)
    clean.append(ck)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=150)
    ctx = browser.new_context(viewport={"width":1280,"height":900}, locale="en-US")
    ctx.add_cookies(clean)
    page = ctx.new_page()

    page.goto("https://www.tiktok.com/upload", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)

    # Upload video
    page.locator('input[type="file"]').first.set_input_files(str(VIDEO_PATH))
    print("Video uploaded. Waiting for encoding...")

    # Wait for encoding
    for i in range(30):
        page.wait_for_timeout(4000)
        try:
            page.locator('[contenteditable="true"]').first.wait_for(state="attached", timeout=1000)
            print(f"  Ready (~{(i+1)*4}s)")
            break
        except PlaywrightTimeoutError:
            print(f"  Encoding... ({(i+1)*4}s)")

    page.wait_for_timeout(1000)

    # Dismiss overlay
    try:
        page.locator('[data-test-id="overlay"]').first.wait_for(state="visible", timeout=2000)
        page.keyboard.press("Escape")
        page.wait_for_timeout(800)
        print("Overlay dismissed")
    except PlaywrightTimeoutError:
        pass

    # Step 1: Click Edit cover (slow so you can watch)
    print("\n[STEP 1] Clicking Edit cover...")
    page.wait_for_timeout(1000)
    loc = page.locator('[data-e2e="cover_container"] .edit-container').first
    loc.dispatch_event("click")
    print("  Clicked. Watch the browser now!")
    page.wait_for_timeout(3000)  # pause so you can see

    # Step 2: Click Upload tab
    print("\n[STEP 2] Clicking Upload tab...")
    page.wait_for_timeout(500)
    upload_tab = page.locator('button:has-text("Upload")').first
    upload_tab.dispatch_event("click")
    print("  Clicked Upload tab. Watch the browser!")
    page.wait_for_timeout(3000)  # pause so you can see

    # Step 3: Upload cover image
    print("\n[STEP 3] Uploading cover image...")
    file_input = page.locator('input[type="file"][accept*="image"]').first
    file_input.set_input_files(str(COVER_PATH))
    print("  Image set. Watch the browser!")
    page.wait_for_timeout(5000)  # pause so you can see

    # Step 4: Look for confirm button
    print("\n[STEP 4] Looking for confirm button...")
    for sel in ['[data-e2e="cover-confirm-btn"]', 'button:has-text("Confirm")',
                'button:has-text("Save")', 'button:has-text("Done")',
                'button:has-text("Apply")', 'button:has-text("OK")']:
        try:
            btn = page.locator(sel).first
            btn.wait_for(state="visible", timeout=2000)
            print(f"  Found confirm button: {sel}")
            btn.dispatch_event("click")
            print("  Clicked confirm!")
            break
        except PlaywrightTimeoutError:
            print(f"  Not found: {sel}")

    print("\n=== ALL DONE === Browser stays open for 120s so you can check the result!")
    page.wait_for_timeout(120000)
    browser.close()
