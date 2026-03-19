import json
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

COOKIES_PATH = Path(__file__).parent / "tiktok_cookies.json"
VIDEO_PATH = Path(__file__).parent.parent / "docs" / "sns_videos" / "20260318_008_tiktok.mp4"
SS_DIR = Path(__file__).parent / "logs"
SS_DIR.mkdir(exist_ok=True)

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
    page.locator('input[type="file"]').first.set_input_files(str(VIDEO_PATH))
    print("Uploaded. Waiting...")

    for i in range(30):
        page.wait_for_timeout(4000)
        try:
            page.locator('[contenteditable="true"]').first.wait_for(state="attached", timeout=1000)
            print(f"  Ready (~{(i+1)*4}s)")
            break
        except PlaywrightTimeoutError:
            print(f"  Encoding... ({(i+1)*4}s)")

    page.wait_for_timeout(1000)
    try:
        page.locator('[data-test-id="overlay"]').first.wait_for(state="visible", timeout=2000)
        page.keyboard.press("Escape")
        page.wait_for_timeout(800)
    except PlaywrightTimeoutError:
        pass

    # SS before clicking Edit cover
    page.screenshot(path=str(SS_DIR / "ss1_before_cover.png"))
    print("SS1: before Edit cover click")

    # Click Edit cover
    page.locator('[data-e2e="cover_container"] .edit-container').first.dispatch_event("click")
    page.wait_for_timeout(2000)

    # SS after clicking Edit cover (modal should be open)
    page.screenshot(path=str(SS_DIR / "ss2_after_cover_click.png"))
    print("SS2: after Edit cover click (modal open?)")

    # Dump all visible buttons
    btns = page.evaluate("""
        () => [...document.querySelectorAll('button')].map(b => ({
            text: b.textContent.trim().slice(0,40),
            visible: b.offsetParent !== null,
            class: b.className.slice(0,60),
        })).filter(b => b.visible && b.text)
    """)
    print("\nVisible buttons after Edit cover click:")
    for b in btns:
        print(" ", b)

    browser.close()
    print("\nScreenshots saved to scripts/logs/")
