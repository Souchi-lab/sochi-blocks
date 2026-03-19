#!/usr/bin/env python3
"""
Generate answer images (all pieces visible) for a list of puzzles.

Outputs: docs/images/{YYYYMMDD}/{NNN}/answer_3d_x.png
         docs/images/{YYYYMMDD}/{NNN}/answer_3d_y.png

Usage:
  # Single puzzle
  python scripts/generate_answer_images.py --puzzle_id 20260317_002

  # Multiple puzzles
  python scripts/generate_answer_images.py \
    --puzzle_id 20260318_005 20260317_002 20260317_003 20260318_004 \
                20260318_006 20260316_002 20260316_003 20260317_004 \
                20260318_007 20260315_002 20260315_003 20260316_004
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_instagram_images import (
    PROJECT_ROOT,
    capture_3d_images_answer,
    wait_for_dev_server,
    DEV_SERVER_URL,
)
import subprocess

DOCS_IMAGES = PROJECT_ROOT / "docs" / "images"


def puzzle_id_to_dir(puzzle_id: str) -> Path:
    """Convert '20260317_002' -> docs/images/20260317/002"""
    date_part, seq_part = puzzle_id.split("_")
    return DOCS_IMAGES / date_part / seq_part


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate answer images for puzzles")
    parser.add_argument(
        "--puzzle_id",
        nargs="+",
        required=True,
        help="Puzzle ID(s) e.g. 20260317_002",
    )
    args = parser.parse_args()

    # Start dev server once for all puzzles
    server_proc = None
    if not wait_for_dev_server(DEV_SERVER_URL, timeout=2):
        print("Starting Vite dev server ...")
        server_proc = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=str(PROJECT_ROOT / "frontend"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=True,
        )
        if not wait_for_dev_server(DEV_SERVER_URL, timeout=30):
            print("ERROR: Could not start dev server", file=sys.stderr)
            if server_proc:
                server_proc.terminate()
            sys.exit(1)
        print("Dev server ready.")

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            for puzzle_id in args.puzzle_id:
                out_dir = puzzle_id_to_dir(puzzle_id)
                if not out_dir.exists():
                    print(f"[WARN] Directory not found, skipping: {out_dir}")
                    continue

                print(f"\n[{puzzle_id}] Generating answer images -> {out_dir}")
                page = browser.new_page(viewport={"width": 1080, "height": 1080})

                for angle, filename in [("x", "answer_3d_x.png"), ("y", "answer_3d_y.png")]:
                    url = (
                        f"{DEV_SERVER_URL}/"
                        f"?puzzle_id={puzzle_id}"
                        f"&mode=capture"
                        f"&capture_all=1"
                        f"&angle={angle}"
                    )
                    page.goto(url)
                    page.wait_for_function(
                        "window.__CAPTURE_READY__ === true",
                        timeout=15000,
                    )
                    page.wait_for_timeout(300)
                    out_path = out_dir / filename
                    page.screenshot(path=str(out_path))
                    print(f"  -> {out_path}")

                page.close()

            browser.close()
    finally:
        if server_proc:
            server_proc.terminate()
            print("\nDev server stopped.")

    print("\nDone.")


if __name__ == "__main__":
    main()
