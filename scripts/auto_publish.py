#!/usr/bin/env python3
"""
Auto-publish a puzzle: select from DB, generate images, deploy to GitHub Pages.

Usage:
  python scripts/auto_publish.py --difficulty easy
  python scripts/auto_publish.py --difficulty medium
  python scripts/auto_publish.py --difficulty hard
  python scripts/auto_publish.py --all   # publish easy + medium + hard at once
"""

import argparse
import json
import os
import random
import sys
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, text

# --- Paths ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PUZZLE_DIR = PROJECT_ROOT / "frontend" / "public" / "puzzles"
DOCS_DIR = PROJECT_ROOT / "docs"
PAGES_BASE_URL = "https://souchi-lab.github.io/sochi-blocks"

# --- Import from sibling ---
sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_instagram_images import (
    generate_layer_image,
    capture_3d_images,
    load_piece_colors,
    load_master_pieces,
)

ALL_PIECES = list("FILNPTUVWXYZ")

DIFFICULTY_MAP = {
    "easy":   {"remove": 2, "label": "Easy",   "id": "a1b2c3d4-0001-4000-8000-000000000001"},
    "medium": {"remove": 4, "label": "Medium", "id": "a1b2c3d4-0002-4000-8000-000000000002"},
    "hard":   {"remove": 6, "label": "Hard",   "id": "a1b2c3d4-0003-4000-8000-000000000003"},
}

PUZZLE_TYPE_ID = "4cfc344d-5137-4e44-8ed1-60c5810f6a4f"
AUTHOR_ID = "f44c725b-8032-43cf-92aa-a3342a90ac63"


def get_engine():
    db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/sochi_blocks")
    return create_engine(db_url)


def get_fingerprint(engine, puzzle_name: str) -> str:
    """Get a string fingerprint of a puzzle's cell layout for similarity comparison."""
    q = text("""
        SELECT trim(c.value) as piece
        FROM master_base_puzzle_cell c
        JOIN master_base_puzzle p ON c.base_puzzle_id = p.id
        WHERE p.name = :name
        ORDER BY c.z, c.y DESC, c.x
    """)
    with engine.connect() as conn:
        rows = conn.execute(q, {"name": puzzle_name}).fetchall()
    return "".join(r.piece for r in rows)


def similarity(fp1: str, fp2: str) -> float:
    """Fraction of cells with the same piece in the same position."""
    if len(fp1) != len(fp2):
        return 0.0
    matches = sum(1 for a, b in zip(fp1, fp2) if a == b)
    return matches / len(fp1)


def select_puzzle(engine, recent_limit: int = 5) -> str:
    """Select a puzzle that is dissimilar to recently published ones."""
    # Get recently published base puzzle names
    q_recent = text("""
        SELECT bp.name
        FROM content_puzzle cp
        JOIN master_base_puzzle bp ON cp.base_puzzle_id = bp.id
        ORDER BY cp.published_at DESC NULLS LAST, cp.created_at DESC
        LIMIT :lim
    """)
    with engine.connect() as conn:
        recent_rows = conn.execute(q_recent, {"lim": recent_limit}).fetchall()
    recent_names = [r.name for r in recent_rows]

    # Get all published base puzzle IDs to exclude
    q_used = text("SELECT DISTINCT bp.name FROM content_puzzle cp JOIN master_base_puzzle bp ON cp.base_puzzle_id = bp.id")
    with engine.connect() as conn:
        used_names = {r.name for r in conn.execute(q_used).fetchall()}

    # Get all available puzzles
    q_all = text("SELECT name FROM master_base_puzzle ORDER BY name")
    with engine.connect() as conn:
        all_names = [r.name for r in conn.execute(q_all).fetchall()]

    # Filter out already used
    candidates = [n for n in all_names if n not in used_names]
    if not candidates:
        # If all used, allow reuse but still pick dissimilar
        candidates = all_names
        print(f"  Warning: all {len(all_names)} puzzles used, allowing reuse")

    # If no recent puzzles, just pick random
    if not recent_names:
        chosen = random.choice(candidates)
        print(f"  No recent puzzles, randomly selected: {chosen}")
        return chosen

    # Compute fingerprints of recent puzzles
    recent_fps = {name: get_fingerprint(engine, name) for name in recent_names}

    # Sample candidates (for performance, max 200)
    if len(candidates) > 200:
        sample = random.sample(candidates, 200)
    else:
        sample = candidates

    # Find least similar to any recent puzzle
    best_name = sample[0]
    best_min_sim = 1.0

    for cand in sample:
        fp = get_fingerprint(engine, cand)
        max_sim = max(similarity(fp, rfp) for rfp in recent_fps.values())
        if max_sim < best_min_sim:
            best_min_sim = max_sim
            best_name = cand

    print(f"  Selected: {best_name} (max similarity to recent: {best_min_sim:.1%})")
    return best_name


def export_puzzle_json(engine, puzzle_name: str, pub_id: str) -> Path:
    """Export puzzle from DB to frontend/public/puzzles/ using pub_id as filename."""
    q = text("""
        SELECT c.x, c.y, c.z, trim(c.value) as piece
        FROM master_base_puzzle_cell c
        JOIN master_base_puzzle p ON c.base_puzzle_id = p.id
        WHERE p.name = :name
        ORDER BY c.z, c.y, c.x
    """)
    with engine.connect() as conn:
        rows = conn.execute(q, {"name": puzzle_name}).fetchall()

    cells = [{"x": r.x, "y": r.y, "z": r.z, "piece": r.piece} for r in rows]
    max_x = max(r.x for r in rows) + 1
    max_y = max(r.y for r in rows) + 1
    max_z = max(r.z for r in rows) + 1

    data = {
        "puzzle_id": pub_id,
        "grid": {"x": max_x, "y": max_y, "z": max_z},
        "cells": cells,
    }

    PUZZLE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PUZZLE_DIR / f"puzzle_{pub_id}.json"
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2)
    return out_path


def save_to_db(engine, puzzle_name: str, difficulty: str, removed: list[str], code: str):
    """Save published puzzle to content_puzzle."""
    diff_cfg = DIFFICULTY_MAP[difficulty]
    now = datetime.utcnow()

    q_bp = text("SELECT id FROM master_base_puzzle WHERE name = :name")
    with engine.connect() as conn:
        bp_id = conn.execute(q_bp, {"name": puzzle_name}).fetchone().id

    q_insert = text("""
        INSERT INTO content_puzzle
            (id, base_puzzle_id, code, title, description, difficulty_id,
             puzzle_type_id, author_id, removed_pieces, created_at, updated_at, published_at)
        VALUES
            (:id, :bp_id, :code, :title, :desc, :diff_id,
             :pt_id, :author_id, :removed, :now, :now, :now)
    """)
    with engine.connect() as conn:
        conn.execute(q_insert, {
            "id": str(uuid.uuid4()),
            "bp_id": str(bp_id),
            "code": code,
            "title": f"Puzzle {code} ({diff_cfg['label']})",
            "desc": f"Base: {puzzle_name}, Removed: {','.join(removed)}",
            "diff_id": diff_cfg["id"],
            "pt_id": PUZZLE_TYPE_ID,
            "author_id": AUTHOR_ID,
            "removed": removed,
            "now": now,
        })
        conn.commit()
    print(f"  [OK] Saved to content_puzzle: {code}")


def publish_one(engine, difficulty: str, seq_number: int | None = None):
    """Publish a single puzzle for the given difficulty."""
    diff_cfg = DIFFICULTY_MAP[difficulty]
    n_remove = diff_cfg["remove"]

    print(f"\n{'='*60}")
    print(f"  Difficulty: {diff_cfg['label']} (remove {n_remove} pieces)")
    print(f"{'='*60}")

    # 1) Select dissimilar puzzle
    print("[1/5] Selecting puzzle...")
    puzzle_name = select_puzzle(engine)

    # 2) Determine pub_id = YYYYMMDD_### (date-based unique ID)
    today = datetime.utcnow()
    date_str = today.strftime("%Y%m%d")
    if seq_number is None:
        q_today = text("""
            SELECT count(*) as cnt FROM content_puzzle
            WHERE DATE(published_at) = :today
        """)
        with engine.connect() as conn:
            seq_number = conn.execute(q_today, {"today": today.date()}).fetchone().cnt + 1
    pub_id = f"{date_str}_{seq_number:03d}"

    # 3) Export JSON from DB using pub_id as filename
    print("[2/5] Exporting puzzle JSON...")
    src_json = export_puzzle_json(engine, puzzle_name, pub_id)
    print(f"  [OK] {src_json}")

    # 4) Choose removed pieces
    removed = sorted(random.sample(ALL_PIECES, n_remove))
    removed_str = ",".join(removed)
    print(f"  Removed pieces: {removed}")

    # 5) Write puzzle JSON to docs/ with removed_pieces embedded
    dst_puzzles = DOCS_DIR / "puzzles"
    dst_puzzles.mkdir(parents=True, exist_ok=True)
    dst_json = dst_puzzles / f"puzzle_{pub_id}.json"

    with open(src_json) as f:
        puzzle_data = json.load(f)
    puzzle_data["removed_pieces"] = removed
    # docs/puzzles/ — minified
    with open(dst_json, "w") as f:
        json.dump(puzzle_data, f, separators=(",", ":"))
    print(f"  [OK] docs JSON -> {dst_json}")
    # frontend/public/puzzles/ — also embed removed_pieces for viewer
    with open(src_json, "w") as f:
        json.dump(puzzle_data, f, indent=2)
    print(f"  [OK] frontend JSON updated -> {src_json}")

    # 6) Generate Instagram images into docs/images/YYYYMMDD/###/
    img_dir = DOCS_DIR / "images" / date_str / f"{seq_number:03d}"
    img_dir.mkdir(parents=True, exist_ok=True)

    colors = load_piece_colors()
    piece_shapes = load_master_pieces()

    print("[3/5] Generating layer image...")
    generate_layer_image(src_json, colors, set(removed), img_dir / "layer.png", piece_shapes)

    print("[4/5] Generating 3D captures...")
    capture_3d_images(pub_id, removed_str, img_dir)

    # Rename 3D files (capture_3d_images now outputs 02_3d_x.png / 03_3d_y.png)
    for old_name, new_name in [
        ("02_3d_x.png", "3d_x.png"),
        ("03_3d_y.png", "3d_y.png"),
    ]:
        old_path = img_dir / old_name
        new_path = img_dir / new_name
        if old_path.exists():
            old_path.replace(new_path)

    # 7) Save to DB
    print("[5/5] Saving to database...")
    save_to_db(engine, puzzle_name, difficulty, removed, pub_id)

    # 8) Print result
    viewer_url = f"{PAGES_BASE_URL}/viewer.html?puzzle_id={pub_id}"
    print(f"\n  [OK] Published: {pub_id}")
    print(f"  [LINK] {viewer_url}")
    print(f"  Images: {img_dir}")

    return {
        "code": pub_id,
        "puzzle_name": puzzle_name,
        "difficulty": difficulty,
        "removed": removed,
        "url": viewer_url,
        "img_dir": str(img_dir),
    }


def main():
    parser = argparse.ArgumentParser(description="Auto-publish puzzles")
    parser.add_argument("--difficulty", choices=["easy", "medium", "hard"], help="Single difficulty")
    parser.add_argument("--all", action="store_true", help="Publish easy + medium + hard")
    args = parser.parse_args()

    if not args.difficulty and not args.all:
        parser.error("Specify --difficulty or --all")

    engine = get_engine()
    results = []

    if args.all:
        today = datetime.utcnow().date()
        q_today = text("SELECT count(*) as cnt FROM content_puzzle WHERE DATE(published_at) = :today")
        with engine.connect() as conn:
            today_base = conn.execute(q_today, {"today": today}).fetchone().cnt
        for i, diff in enumerate(["easy", "medium", "hard"], start=1):
            r = publish_one(engine, diff, seq_number=today_base + i)
            results.append(r)
    else:
        r = publish_one(engine, args.difficulty)
        results.append(r)

    # Summary
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    for r in results:
        print(f"  {r['code']:10s} [{r['difficulty']:6s}] {r['puzzle_name']}  removed={r['removed']}")
    print()
    print("  Next steps:")
    print('    git add docs/')
    print('    git commit -m "puzzle: auto-publish"')
    print('    git push origin main')
    print("=" * 60)


if __name__ == "__main__":
    main()
