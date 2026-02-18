#!/usr/bin/env python3
"""
Publish a puzzle for Instagram + GitHub Pages in one command.

Outputs:
  docs/puzzles/puzzle_{id}.json        -- viewer data
  docs/images/{id}/layer.png           -- Instagram image 1
  docs/images/{id}/3d_x.png            -- Instagram image 2
  docs/images/{id}/3d_y.png            -- Instagram image 3

Usage:
  python scripts/publish_puzzle.py --puzzle_id 5x4x3_0010 --removed_pieces V,W
"""

import argparse
import json
import shutil
import sys
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Publish puzzle: generate Instagram images + deploy to GitHub Pages"
    )
    parser.add_argument("--puzzle_id", required=True, help="e.g. 5x4x3_0010")
    parser.add_argument("--removed_pieces", default="", help="e.g. V,W")
    args = parser.parse_args()

    puzzle_id: str = args.puzzle_id
    removed_pieces_str: str = args.removed_pieces
    removed_set = (
        {s.strip() for s in removed_pieces_str.split(",") if s.strip()}
        if removed_pieces_str
        else set()
    )

    # --- 1) Copy puzzle JSON to docs/puzzles/ ---
    src_json = PUZZLE_DIR / f"puzzle_{puzzle_id}.json"
    if not src_json.exists():
        print(f"ERROR: Puzzle file not found: {src_json}", file=sys.stderr)
        sys.exit(1)

    dst_puzzles = DOCS_DIR / "puzzles"
    dst_puzzles.mkdir(parents=True, exist_ok=True)
    dst_json = dst_puzzles / f"puzzle_{puzzle_id}.json"

    # Embed removed_pieces into the JSON (answer hidden from URL)
    with open(src_json) as f:
        puzzle_data = json.load(f)
    if removed_set:
        puzzle_data["removed_pieces"] = sorted(removed_set)
    elif "removed_pieces" in puzzle_data:
        del puzzle_data["removed_pieces"]
    with open(dst_json, "w") as f:
        json.dump(puzzle_data, f, separators=(",", ":"))
    print(f"[OK] Puzzle JSON  -> {dst_json}")
    if removed_set:
        print(f"     (removed_pieces embedded: {sorted(removed_set)})")

    # --- 2) Generate Instagram images to docs/images/{id}/ ---
    img_dir = DOCS_DIR / "images" / puzzle_id
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
    capture_3d_images(puzzle_id, removed_pieces_str, img_dir)

    # Rename 3D files to clean names
    for old_name, new_name in [
        (f"{puzzle_id}_3d_x.png", "3d_x.png"),
        (f"{puzzle_id}_3d_y.png", "3d_y.png"),
    ]:
        old_path = img_dir / old_name
        new_path = img_dir / new_name
        if old_path.exists():
            old_path.replace(new_path)
            print(f"[OK] {new_name:14s} -> {new_path}")

    # --- 3) Print viewer URL (clean, no answer in URL) ---
    viewer_url = f"{PAGES_BASE_URL}/viewer.html?puzzle_id={puzzle_id}"

    print()
    print("=" * 60)
    print(f"[LINK] Viewer URL:")
    print(f"   {viewer_url}")
    print()
    print(f"[NEXT] Next steps:")
    print(f'   git add docs/')
    print(f'   git commit -m "puzzle: {puzzle_id}"')
    print(f'   git push origin main')
    print("=" * 60)


if __name__ == "__main__":
    main()
