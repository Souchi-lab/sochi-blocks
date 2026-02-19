#!/usr/bin/env python3
"""
Publish a puzzle for Instagram + GitHub Pages in one command.

Outputs:
  docs/puzzles/puzzle_{pub_id}.json          -- viewer data
  docs/images/{YYYYMMDD}/{###}/layer.png     -- Instagram image 1
  docs/images/{YYYYMMDD}/{###}/3d_x.png      -- Instagram image 2
  docs/images/{YYYYMMDD}/{###}/3d_y.png      -- Instagram image 3

Usage:
  python scripts/publish_puzzle.py --base 5x4x3_0010 --pub_id 20260219_001 --removed_pieces V,W

  If --pub_id is omitted, it is auto-generated as YYYYMMDD_NNN based on today's
  date and the number of existing docs/puzzles/ files.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Import from sibling module
sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_instagram_images import (
    PUZZLE_DIR,
    PROJECT_ROOT,
    generate_layer_image,
    capture_3d_images,
    load_piece_colors,
    load_master_pieces,
)

DOCS_DIR = PROJECT_ROOT / "docs"
PAGES_BASE_URL = "https://souchi-lab.github.io/sochi-blocks"


def _next_pub_id() -> str:
    """Auto-generate next pub_id (YYYYMMDD_NNN) from today's date and existing count."""
    today = datetime.utcnow()
    date_str = today.strftime("%Y%m%d")
    existing = list((DOCS_DIR / "puzzles").glob(f"puzzle_{date_str}_*.json"))
    seq = len(existing) + 1
    return f"{date_str}_{seq:03d}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Publish puzzle: generate Instagram images + deploy to GitHub Pages"
    )
    parser.add_argument("--base", required=True, help="Base puzzle name, e.g. 5x4x3_0010")
    parser.add_argument("--pub_id", default=None, help="Public ID, e.g. 20260219_001 (auto if omitted)")
    parser.add_argument("--removed_pieces", default="", help="e.g. V,W")
    args = parser.parse_args()

    base_name: str = args.base
    pub_id: str = args.pub_id or _next_pub_id()
    removed_pieces_str: str = args.removed_pieces
    removed_set = (
        {s.strip() for s in removed_pieces_str.split(",") if s.strip()}
        if removed_pieces_str
        else set()
    )

    # Parse date and seq from pub_id (format: YYYYMMDD_NNN)
    try:
        date_part, seq_part = pub_id.split("_", 1)
        img_dir = DOCS_DIR / "images" / date_part / seq_part
    except ValueError:
        print(f"ERROR: pub_id must be in YYYYMMDD_NNN format, got: {pub_id}", file=sys.stderr)
        sys.exit(1)

    # --- 1) Copy puzzle JSON to docs/puzzles/ with pub_id as filename ---
    src_json = PUZZLE_DIR / f"puzzle_{base_name}.json"
    if not src_json.exists():
        print(f"ERROR: Puzzle file not found: {src_json}", file=sys.stderr)
        sys.exit(1)

    dst_puzzles = DOCS_DIR / "puzzles"
    dst_puzzles.mkdir(parents=True, exist_ok=True)
    dst_json = dst_puzzles / f"puzzle_{pub_id}.json"

    # Also copy to frontend/public/puzzles/ with pub_id so 3D capture can load it
    fe_pub_json = PUZZLE_DIR / f"puzzle_{pub_id}.json"

    with open(src_json) as f:
        puzzle_data = json.load(f)
    puzzle_data["puzzle_id"] = pub_id
    if removed_set:
        puzzle_data["removed_pieces"] = sorted(removed_set)
    elif "removed_pieces" in puzzle_data:
        del puzzle_data["removed_pieces"]

    with open(dst_json, "w") as f:
        json.dump(puzzle_data, f, separators=(",", ":"))
    print(f"[OK] Puzzle JSON  -> {dst_json}")

    # Also write to frontend/public/puzzles/ (with removed_pieces for viewer)
    with open(fe_pub_json, "w") as f:
        json.dump(puzzle_data, f, indent=2)
    print(f"[OK] Frontend JSON -> {fe_pub_json}")

    if removed_set:
        print(f"     (removed_pieces embedded: {sorted(removed_set)})")

    # --- 2) Generate Instagram images to docs/images/YYYYMMDD/NNN/ ---
    img_dir.mkdir(parents=True, exist_ok=True)

    colors = load_piece_colors()
    piece_shapes = load_master_pieces()

    # 2a) Layer image
    print("[1/3] 2D Layer image")
    layer_path = img_dir / "layer.png"
    generate_layer_image(src_json, colors, removed_set, layer_path, piece_shapes)
    print(f"[OK] Layer image  -> {layer_path}")

    # 2b) 3D captures
    print("[2/3] 3D Angle X")
    print("[3/3] 3D Angle Y")
    capture_3d_images(pub_id, removed_pieces_str, img_dir)

    # Rename 3D files to clean names
    for old_name, new_name in [
        (f"{pub_id}_3d_x.png", "3d_x.png"),
        (f"{pub_id}_3d_y.png", "3d_y.png"),
    ]:
        old_path = img_dir / old_name
        new_path = img_dir / new_name
        if old_path.exists():
            old_path.replace(new_path)
            print(f"[OK] {new_name:14s} -> {new_path}")

    # --- 3) Print viewer URL ---
    viewer_url = f"{PAGES_BASE_URL}/viewer.html?puzzle_id={pub_id}"

    print()
    print("=" * 60)
    print(f"[ID]   {pub_id}")
    print(f"[BASE] {base_name}")
    print(f"[LINK] Viewer URL:")
    print(f"   {viewer_url}")
    print()
    print(f"[NEXT] Next steps:")
    print(f'   git add docs/')
    print(f'   git commit -m "puzzle: {pub_id}"')
    print(f'   git push origin main')
    print("=" * 60)


if __name__ == "__main__":
    main()
