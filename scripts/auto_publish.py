#!/usr/bin/env python3
"""
Auto-publish puzzles end-to-end: DB → images → caption → GitHub Pages.

One command to do everything for a full day:
  python scripts/auto_publish.py --all

Flow per puzzle:
  1) Select dissimilar puzzle from DB
  2) Export puzzle JSON
  3) Generate 2D layer image
  4) Generate 3D captures (Playwright)
  5) Save to DB + write caption.txt / url.txt
  6) git add / commit / push → GitHub Pages live

Single difficulty:
  python scripts/auto_publish.py --difficulty easy
"""

import argparse
import json
import os
import random
import subprocess as _sp
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
import time
import urllib.request
import urllib.error

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
    write_caption,
)

ALL_PIECES = list("FILNPTUVWXYZ")

_DIFFICULTY_LABELS = {
    "a1b2c3d4-0001-4000-8000-000000000001": "Easy",
    "a1b2c3d4-0002-4000-8000-000000000002": "Medium",
    "a1b2c3d4-0003-4000-8000-000000000003": "Hard",
}

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


_REMOVE_TO_DIFF = {2: "Easy", 4: "Medium", 6: "Hard"}


def generate_manifest(engine) -> None:
    """Regenerate docs/puzzles/manifest.json from DB + puzzle JSONs."""
    q = text("""
        SELECT code, difficulty_id, published_at
        FROM content_puzzle
        ORDER BY published_at DESC NULLS LAST, code DESC
    """)
    with engine.connect() as conn:
        rows = conn.execute(q).fetchall()

    manifest = []
    for row in rows:
        puzzle_json = PUZZLE_DIR / f"puzzle_{row.code}.json"
        if not puzzle_json.exists():
            continue
        with open(puzzle_json) as f:
            pdata = json.load(f)
        removed = pdata.get("removed_pieces", [])
        diff_label = _DIFFICULTY_LABELS.get(str(row.difficulty_id)) \
            or _REMOVE_TO_DIFF.get(len(removed), "")
        date_str = row.published_at.strftime("%Y-%m-%d") if row.published_at else ""
        manifest.append({
            "id": row.code,
            "date": date_str,
            "difficulty": diff_label,
            "removed": removed,
        })

    manifest_path = DOCS_DIR / "puzzles" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, separators=(",", ":"))
    print(f"  [OK] manifest.json ({len(manifest)} puzzles) -> {manifest_path}")


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
    now = datetime.now(timezone.utc)

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
    print("[1/6] Selecting puzzle...")
    puzzle_name = select_puzzle(engine)

    # 2) Determine pub_id = YYYYMMDD_### (date-based unique ID)
    today = datetime.now(timezone.utc)
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
    print("[2/6] Exporting puzzle JSON...")
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

    print("[3/6] Generating layer image...")
    generate_layer_image(src_json, colors, set(removed), img_dir / "layer.png", piece_shapes)

    print("[4/6] Generating 3D captures...")
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

    # 7.5) Generate SNS video
    print("[5/6] Generating SNS video...")
    try:
        _sp.run(["npm", "run", "generate-sns", pub_id],
                cwd=str(PROJECT_ROOT / "frontend"), check=True, shell=True)
        video_src_dir = PROJECT_ROOT / "frontend" / "public" / "sns_videos"
        for ext in ["mp4", "gif"]:
            src = video_src_dir / f"{pub_id}.{ext}"
            if src.exists():
                dst = img_dir / f"{pub_id}.{ext}"
                src.replace(dst)
                print(f"  [OK] Produced {ext} -> {dst}")
    except Exception as e:
        print(f"  [WARN] SNS video generation failed: {e}")

    # 7) Save to DB
    print("[6/6] Saving to database...")
    save_to_db(engine, puzzle_name, difficulty, removed, pub_id)

    # 8) caption.txt alongside images
    write_caption(img_dir, pub_id, diff_cfg["label"])
    print(f"  [OK] caption.txt -> {img_dir / 'caption.txt'}")

    print(f"  Images/Video: {img_dir}")

    # 9) Generate shareable HTML for social media (OG tags)
    share_html_dir = DOCS_DIR / "share"
    share_html_dir.mkdir(parents=True, exist_ok=True)
    share_html_path = share_html_dir / f"{pub_id}.html"
    
    # Image for OG tag (layer.png)
    image_url = f"{PAGES_BASE_URL}/images/{date_str}/{seq_number:03d}/layer.png"
    final_viewer_url = f"{PAGES_BASE_URL}/viewer.html?puzzle_id={pub_id}"
    
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>SoChi BLOCKS Puzzle {pub_id}</title>
    <meta property="og:title" content="SoChi BLOCKS Puzzle {pub_id} ({diff_cfg['label']})">
    <meta property="og:description" content="Can you solve this puzzle? Tap to view in 3D!">
    <meta property="og:image" content="{image_url}">
    <meta property="og:url" content="{PAGES_BASE_URL}/share/{pub_id}.html">
    <meta property="og:type" content="website">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="SoChi BLOCKS Puzzle {pub_id}">
    <meta name="twitter:description" content="Can you solve this? #SoChiBLOCKS">
    <meta name="twitter:image" content="{image_url}">
    
    <!-- Redirect to actual viewer -->
    <meta http-equiv="refresh" content="0; url={final_viewer_url}">
    <script>window.location.href = "{final_viewer_url}";</script>
</head>
<body>
    <p>Redirecting to puzzle viewer... <a href="{final_viewer_url}">Click here</a> if not redirected.</p>
</body>
</html>
"""
    with open(share_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"  [OK] share html -> {share_html_path}")

    share_url = f"{PAGES_BASE_URL}/share/{pub_id}.html"

    return {
        "code": pub_id,
        "puzzle_name": puzzle_name,
        "difficulty": difficulty,
        "removed": removed,
        "url": final_viewer_url,
        "share_url": share_url,
        "img_dir": str(img_dir),
    }


def main():
    parser = argparse.ArgumentParser(description="Auto-publish puzzles")
    parser.add_argument("--difficulty", choices=["easy", "medium", "hard"], help="Single difficulty")
    parser.add_argument("--all", action="store_true", help="Publish easy + medium + hard")
    parser.add_argument("--dir", help="Manual directory for posting (skips generation)")
    parser.add_argument("--twitter", action="store_true", help="Post results to Twitter (X)")
    parser.add_argument("--instagram", action="store_true", help="Post results to Instagram")
    args = parser.parse_args()

    if not args.difficulty and not args.all and not args.dir:
        parser.error("Specify --difficulty, --all, or --dir")

    engine = get_engine()
    results = []

    if args.all:
        today = datetime.now(timezone.utc).date()
        q_today = text("SELECT count(*) as cnt FROM content_puzzle WHERE DATE(published_at) = :today")
        with engine.connect() as conn:
            today_base = conn.execute(q_today, {"today": today}).fetchone().cnt
        for i, diff in enumerate(["easy", "medium", "hard"], start=1):
            r = publish_one(engine, diff, seq_number=today_base + i)
            results.append(r)
    elif args.dir:
        # Manual mode
        d = Path(args.dir)
        if not d.exists():
            print(f"Error: {d} does not exist.")
            sys.exit(1)
        # Try to extract code from path (e.g. docs/images/20260307/001 -> 20260307_001)
        # Or just use the last two parts
        try:
            code = f"{d.parent.name}_{d.name}"
        except:
            code = d.name
            
        results.append({
            "code": code,
            "puzzle_name": "Manual",
            "difficulty": "Unknown",
            "removed": [],
            "url": f"{PAGES_BASE_URL}/viewer.html?puzzle_id={code}",
            "img_dir": str(d),
        })
    else:
        r = publish_one(engine, args.difficulty)
        results.append(r)

    # Manual mode enrichment: Generate share HTML if it doesn't exist
    if args.dir:
        for r in results:
            share_html_dir = DOCS_DIR / "share"
            share_html_dir.mkdir(parents=True, exist_ok=True)
            share_html_path = share_html_dir / f"{r['code']}.html"
            
            # Use layer.png from the specified directory
            d = Path(r["img_dir"])
            try:
                # Try to get relative path from 'docs'
                parts = d.resolve().parts
                idx = parts.index("docs")
                rel_url = "/".join(parts[idx+1:])
                image_url = f"{PAGES_BASE_URL}/{rel_url}/layer.png"
            except:
                image_url = f"{PAGES_BASE_URL}/images/placeholder.png"

            html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>SoChi BLOCKS Puzzle {r['code']}</title>
    <meta property="og:title" content="SoChi BLOCKS Puzzle {r['code']}">
    <meta property="og:description" content="Can you solve this puzzle? Tap to view in 3D!">
    <meta property="og:image" content="{image_url}">
    <meta property="og:url" content="{PAGES_BASE_URL}/share/{r['code']}.html">
    <meta property="og:type" content="website">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="SoChi BLOCKS Puzzle {r['code']}">
    <meta name="twitter:description" content="Can you solve this? #SoChiBLOCKS">
    <meta name="twitter:image" content="{image_url}">
    
    <meta http-equiv="refresh" content="0; url={r['url']}">
    <script>window.location.href = "{r['url']}";</script>
</head>
<body>
    <p>Redirecting to puzzle viewer... <a href="{r['url']}">Click here</a> if not redirected.</p>
</body>
</html>
"""
            with open(share_html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            r["share_url"] = f"{PAGES_BASE_URL}/share/{r['code']}.html"
            print(f"  [OK] Generated manual share html -> {share_html_path}")

    # Summary
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    for r in results:
        print(f"  {r['code']:10s} [{r['difficulty']:6s}] {r['puzzle_name']}  removed={r['removed']}")
        print(f"             {r['url']}")
    print("=" * 60)

    # Regenerate manifest.json
    print("\n  Regenerating manifest.json...")
    generate_manifest(engine)

    # Git publish (only if NOT in manual mode)
    if not args.dir:
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        codes = " ".join(r["code"] for r in results)
        commit_msg = f"puzzle: publish {date_str} ({codes})"

        print("\n  Publishing to GitHub Pages...")
        try:
            _sp.run(["git", "add", "docs/", "frontend/public/puzzles/"],
                    check=True, cwd=str(PROJECT_ROOT))
            _sp.run(["git", "commit", "-m", commit_msg],
                    check=True, cwd=str(PROJECT_ROOT))
            _sp.run(["git", "push", "origin", "main"],
                    check=True, cwd=str(PROJECT_ROOT))
            print("  [OK] Pushed to GitHub Pages!")
        except Exception as e:
            print(f"  [WARN] git push failed: {e}")
            print("  Run manually:")
            print('    git push origin main')

    # Twitter publish
    if args.twitter:
        print("\n  Posting to Twitter...")
        for r in results:
            print(f"  [TX] Posting {r['code']} ...")
            try:
                # Use subprocess to run the specific script with poetry
                # Pass share_url instead of the viewer url
                _sp.run(["poetry", "run", "python", "scripts/publish_twitter.py", 
                         "--dir", r["img_dir"], "--link-only", "--url", r["share_url"]],
                        check=True, cwd=str(PROJECT_ROOT))
            except Exception as e:
                print(f"  [WARN] Twitter post failed for {r['code']}: {e}")

    # Instagram publish
    if args.instagram:
        print("\n  Posting to Instagram...")
        # First, ensure at least one asset is live on GitHub Pages
        # The Instagram API requires media to be publicly accessible via URL.
        # Since we just pushed to GitHub Pages, we wait a bit for it to be live.
        for r in results:
            print(f"  [IG] Waiting for media to be live: {r['code']} ...")
            # Check for layer.png as a proxy for the whole folder
            asset_url = f"{PAGES_BASE_URL}/images/{r['code'].replace('_', '/')}/layer.png"
            
            max_retries = 15
            retry_wait = 20 # seconds
            is_live = False
            
            for attempt in range(1, max_retries + 1):
                try:
                    with urllib.request.urlopen(asset_url) as response:
                        if response.getcode() == 200:
                            print(f"    [OK] Media is live! (Attempt {attempt})")
                            is_live = True
                            break
                except (urllib.error.HTTPError, urllib.error.URLError):
                    pass
                
                print(f"    [...] Still waiting for GitHub Pages... (Attempt {attempt}/{max_retries})")
                time.sleep(retry_wait)
            
            if is_live:
                try:
                    # Use subprocess to run the specific script with poetry
                    _sp.run(["poetry", "run", "python", "scripts/publish_instagram.py", 
                             "--dir", r["img_dir"], "--base-url", PAGES_BASE_URL],
                            check=True, cwd=str(PROJECT_ROOT))
                except Exception as e:
                    print(f"  [WARN] Instagram post failed for {r['code']}: {e}")
            else:
                print(f"  [ERROR] Media did not become live in time. Skipping Instagram post for {r['code']}.")

    print("=" * 60)


if __name__ == "__main__":
    main()
