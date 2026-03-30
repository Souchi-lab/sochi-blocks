#!/usr/bin/env python3
"""
Auto-publish puzzles end-to-end: DB → images → caption → GitHub Pages.

One command to do everything for a full day:
  python scripts/auto_publish.py --all

Single shared puzzle mode:
  python scripts/auto_publish.py --shared-one --difficulty easy --twitter --instagram --tiktok

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
from typing import Any
from pathlib import Path
import time
import urllib.request
import urllib.error

from sqlalchemy import create_engine, text

# Ensure argparse/help text can be printed on Windows terminals even when
# the default code page is not UTF-8.
for _stream_name in ("stdout", "stderr"):
    _stream = getattr(sys, _stream_name, None)
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

# --- Paths ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PUZZLE_DIR = PROJECT_ROOT / "frontend" / "public" / "puzzles"
DOCS_DIR = PROJECT_ROOT / "docs"
PAGES_BASE_URL = "https://souchi-lab.github.io/sochi-blocks"

# --- Import from sibling ---
# Insert project root to sys.path so 'scripts.*' imports work at runtime
sys.path.insert(0, str(PROJECT_ROOT))
from scripts.generate_instagram_images import (
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
    "a1b2c3d4-0004-4000-8000-000000000004": "Hardest",
}

DIFFICULTY_MAP = {
    "easy":    {"remove": 2, "label": "Easy",    "id": "a1b2c3d4-0001-4000-8000-000000000001"},
    "medium":  {"remove": 4, "label": "Medium",  "id": "a1b2c3d4-0002-4000-8000-000000000002"},
    "hard":    {"remove": 6, "label": "Hard",    "id": "a1b2c3d4-0003-4000-8000-000000000003"},
    "hardest": {"remove": 8, "label": "Hardest", "id": "a1b2c3d4-0004-4000-8000-000000000004"},
}

PUZZLE_TYPE_ID = "4cfc344d-5137-4e44-8ed1-60c5810f6a4f"
AUTHOR_ID = "f44c725b-8032-43cf-92aa-a3342a90ac63"


def get_engine():
    db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/sochi_blocks")
    return create_engine(db_url)


_REMOVE_TO_DIFF = {2: "Easy", 4: "Medium", 6: "Hard", 8: "Hardest"}


# ---------------------------------------------------------------------------
# Hook experiment config
# ---------------------------------------------------------------------------

def load_hook_config() -> dict:
    """Load hook experiment config from scripts/hook_config.json.

    Supports two formats:
      Schedule format (recommended):
        {"default_hook_pattern": "B", "daily_schedule": {"2026-03-25": "A", ...}}
        Today's date (YYYY-MM-DD) is looked up in daily_schedule first;
        falls back to default_hook_pattern if the date is not listed.
      Legacy format:
        {"hook_pattern": "A"}

    Returns dict with 'hook_pattern' (A or B), 'source', and optional 'note'.
    Defaults to Pattern B if file is missing or invalid.
    """
    from datetime import date as _date
    config_path = Path(__file__).resolve().parent / "hook_config.json"
    if not config_path.exists():
        return {"hook_pattern": "B", "source": "default", "note": "hook_config.json not found"}
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        today_str = _date.today().isoformat()  # "YYYY-MM-DD"

        if "daily_schedule" in data or "default_hook_pattern" in data:
            # Schedule format
            schedule = data.get("daily_schedule", {})
            default = str(data.get("default_hook_pattern", "B")).upper()
            if today_str in schedule:
                pattern = str(schedule[today_str]).upper()
                source = f"schedule[{today_str}]"
            else:
                pattern = default
                source = "default"
        else:
            # Legacy format
            pattern = str(data.get("hook_pattern", "B")).upper()
            source = "legacy"

        if pattern not in ("A", "B"):
            raise ValueError(f"hook_pattern must be 'A' or 'B', got: {pattern!r}")
        print(f"  [Hook Config] pattern={pattern} source={source}")
        return {"hook_pattern": pattern, "source": source, "note": data.get("note", "")}
    except Exception as e:
        print(f"  [WARN] hook_config.json load error: {e}. Defaulting to Pattern B.")
        return {"hook_pattern": "B", "source": "fallback", "note": str(e)}


def _append_hook_log(puzzle_code: str, hook_pattern: str, video_filename: str, status: str) -> None:
    """Append one row to scripts/logs/hook_log.csv."""
    import csv as _csv
    from datetime import datetime as _dt
    log_dir = Path(__file__).resolve().parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "hook_log.csv"
    write_header = not log_path.exists()
    with open(log_path, "a", newline="", encoding="utf-8") as f:
        writer = _csv.writer(f)
        if write_header:
            writer.writerow(["posted_at", "hook_pattern", "puzzle_code", "video_filename", "status"])
        writer.writerow([_dt.now().isoformat(), hook_pattern, puzzle_code, video_filename, status])
    print(f"  [Hook Log] {puzzle_code} pattern={hook_pattern} status={status}")


def _append_twitter_log(puzzle_code: str, status: str) -> None:
    """Append one row to scripts/logs/twitter_log.csv."""
    import csv as _csv
    from datetime import datetime as _dt
    log_dir = Path(__file__).resolve().parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "twitter_log.csv"
    write_header = not log_path.exists()
    with open(log_path, "a", newline="", encoding="utf-8") as f:
        writer = _csv.writer(f)
        if write_header:
            writer.writerow(["posted_at", "puzzle_code", "status"])
        writer.writerow([_dt.now().isoformat(), puzzle_code, status])
    print(f"  [Twitter Log] {puzzle_code} status={status}")


def generate_manifest(engine) -> None:
    """Regenerate docs/puzzles/manifest.json from DB (single source of truth)."""
    q = text("""
        SELECT code, difficulty_id, published_at, removed_pieces
        FROM content_puzzle
        ORDER BY published_at DESC NULLS LAST, code DESC
    """)
    with engine.connect() as conn:
        rows = conn.execute(q).fetchall()

    manifest = []
    for row in rows:
        # Skip if puzzle JSON doesn't exist on disk yet
        puzzle_json = PUZZLE_DIR / f"puzzle_{row.code}.json"
        if not puzzle_json.exists():
            continue
        removed = list(row.removed_pieces) if row.removed_pieces else []
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
        ON CONFLICT (code) DO NOTHING
    """)
    with engine.connect() as conn:
        result = conn.execute(q_insert, {
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
    if result.rowcount == 0:
        print(f"  [SKIP] Already in DB: {code}")
    else:
        print(f"  [OK] Saved to content_puzzle: {code}")


def _trim_for_sns(pub_id: str, sns_dir: Path) -> None:
    """
    Create platform-specific video cuts from _full.mp4.

    SNS video strategy:
      _tiktok.mp4    = 0-8s  (TikTok: discovery cut, no answer)
      _instagram.mp4 = full  (Instagram: full video with answer, catalog/brand)

    Requires ffmpeg. Skips gracefully if ffmpeg is unavailable or source missing.
    """
    import shutil as _shutil
    full_mp4 = sns_dir / f"{pub_id}_full.mp4"
    if not full_mp4.exists():
        print(f"  [SNS trim] _full.mp4 not found, skipping trim step.")
        return

    # Check for BGM
    bgm_file = PROJECT_ROOT / "assets" / "bgm.mp3"
    has_bgm = bgm_file.exists()

    # TikTok cut: Pattern B (0-8s, no text overlay — current default)
    tiktok_mp4 = sns_dir / f"{pub_id}_tiktok.mp4"
    if not tiktok_mp4.exists():
        try:
            cmd = ["ffmpeg", "-y", "-i", str(full_mp4)]
            if has_bgm:
                cmd.extend(["-stream_loop", "-1", "-i", str(bgm_file)])
            cmd.extend(["-t", "8"])
            if has_bgm:
                cmd.extend(["-c:v", "copy", "-c:a", "aac", "-map", "0:v:0", "-map", "1:a:0", "-shortest"])
            else:
                cmd.extend(["-c", "copy"])
            cmd.append(str(tiktok_mp4))

            _sp.run(cmd, check=True, stdout=_sp.DEVNULL, stderr=_sp.DEVNULL)
            print(f"  [OK] TikTok cut Pattern B (0-8s{' + BGM' if has_bgm else ''}) -> {tiktok_mp4.name}")
        except (FileNotFoundError, _sp.CalledProcessError) as e:
            print(f"  [WARN] TikTok trim failed (ffmpeg required): {e}")

    # TikTok cut: Pattern A (0-8s + drawtext "Can you solve this?" at 0.5-3.0s)
    hook_cfg = load_hook_config()
    if hook_cfg["hook_pattern"] == "A":
        tiktok_A_mp4 = sns_dir / f"{pub_id}_tiktok_A.mp4"
        if not tiktok_A_mp4.exists():
            try:
                cmd = ["ffmpeg", "-y", "-i", str(full_mp4)]
                if has_bgm:
                    cmd.extend(["-stream_loop", "-1", "-i", str(bgm_file)])
                cmd.extend(["-t", "8"])
                cmd.extend([
                    "-vf", (
                        "drawtext="
                        "text='Can you solve this?':"
                        "fontfile='C\\:/Windows/Fonts/arial.ttf':"
                        "fontsize=48:"
                        "fontcolor=white:"
                        "x=(w-text_w)/2:"
                        "y=60:"
                        "shadowx=2:shadowy=2:"
                        "enable='between(t,0.5,3.0)'"
                    )
                ])
                if has_bgm:
                    cmd.extend(["-c:a", "aac", "-map", "0:v:0", "-map", "1:a:0", "-shortest"])
                cmd.append(str(tiktok_A_mp4))

                _sp.run(cmd, check=True, stdout=_sp.DEVNULL, stderr=_sp.DEVNULL)
                print(f"  [OK] TikTok cut Pattern A (drawtext{' + BGM' if has_bgm else ''}) -> {tiktok_A_mp4.name}")
            except (FileNotFoundError, _sp.CalledProcessError) as e:
                print(f"  [WARN] TikTok Pattern A trim failed: {e}")
                print(f"  [WARN] Check ffmpeg drawtext support. Pattern A video not created.")

    # Instagram cut: full video (same as _full.mp4, copy for explicit naming, or mix BGM)
    instagram_mp4 = sns_dir / f"{pub_id}_instagram.mp4"
    if not instagram_mp4.exists():
        try:
            if has_bgm:
                cmd = [
                    "ffmpeg", "-y", "-i", str(full_mp4),
                    "-stream_loop", "-1", "-i", str(bgm_file),
                    "-c:v", "copy", "-c:a", "aac",
                    "-map", "0:v:0", "-map", "1:a:0", "-shortest",
                    str(instagram_mp4)
                ]
                _sp.run(cmd, check=True, stdout=_sp.DEVNULL, stderr=_sp.DEVNULL)
                print(f"  [OK] Instagram video (full + BGM) -> {instagram_mp4.name}")
            else:
                _shutil.copy2(str(full_mp4), str(instagram_mp4))
                print(f"  [OK] Instagram video (full, no BGM) -> {instagram_mp4.name}")
        except Exception as e:
            print(f"  [WARN] Instagram video preparation failed: {e}")


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

    # 7.5) Generate SNS videos (teaser + full)
    print("[5/6] Generating SNS videos (teaser + full)...")
    video_src_dir = PROJECT_ROOT / "frontend" / "public" / "sns_videos"
    sns_dst_dir = DOCS_DIR / "sns_videos"
    sns_dst_dir.mkdir(parents=True, exist_ok=True)
    for mode in ["teaser", "full_play"]:
        try:
            _sp.run(
                ["npm", "run", "generate-sns", "--", pub_id, mode],
                cwd=str(PROJECT_ROOT / "frontend"), check=True, shell=True,
            )
            suffix = "_teaser" if mode == "teaser" else "_full"
            src_mp4 = video_src_dir / f"{pub_id}{suffix}.mp4"
            if src_mp4.exists():
                dst_mp4 = sns_dst_dir / src_mp4.name
                import shutil
                shutil.copy2(str(src_mp4), str(dst_mp4))
                print(f"  [OK] {mode} -> {dst_mp4}")
        except Exception as e:
            print(f"  [WARN] SNS video generation failed ({mode}): {e}")

    # 7.6) Trim SNS videos per platform
    #   _tiktok.mp4    = 0-8s  (TikTok: discovery, no answer)
    #   _instagram.mp4 = full  (Instagram: brand/catalog, answer included)
    _trim_for_sns(pub_id, sns_dst_dir)

    # 7) Save to DB
    print("[6/6] Saving to database...")
    save_to_db(engine, puzzle_name, difficulty, removed, pub_id)

    # 8) caption.txt alongside images
    write_caption(img_dir, pub_id, diff_cfg["label"], removed_pieces=removed)
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
    parser.add_argument(
        "--difficulty",
        choices=["easy", "medium", "hard", "hardest"],
        help="Single difficulty generation, or pair with --shared-one for single shared puzzle mode",
    )
    parser.add_argument("--all", action="store_true", help="Multi-puzzle batch mode: publish easy + medium + hard + hardest")
    parser.add_argument(
        "--shared-one",
        action="store_true",
        help="Single shared puzzle mode: generate 1 puzzle and share it across enabled platforms (requires --difficulty)",
    )
    parser.add_argument("--dir", help="Manual directory for posting (skips generation)")
    parser.add_argument("--twitter", action="store_true", default=True, help="Post results to Twitter (X) [Default: True]")
    parser.add_argument("--no-twitter", action="store_false", dest="twitter", help="Disable Twitter post")
    parser.add_argument("--instagram", action="store_true", help="Post Instagram Carousel (backward compat)")
    parser.add_argument("--also-reel", action="store_true", help="Also post Reel (with --instagram, backward compat)")
    parser.add_argument("--instagram-reel", action="store_true",
                        help="[Instagram Reel] Brand exposure — full video (0-12s) with answer")
    parser.add_argument("--instagram-carousel", action="store_true",
                        help="[Instagram Carousel] Puzzle catalog — layer.png required as cover")
    parser.add_argument("--tiktok", action="store_true", default=True,
                        help="[TikTok] Discovery [Default: True]")
    parser.add_argument("--no-tiktok", action="store_false", dest="tiktok", help="Disable TikTok post")
    parser.add_argument("--tiktok-auto", action="store_true", default=True,
                        help="[TikTok] Auto-click Post [Default: True]")
    parser.add_argument("--no-tiktok-auto", action="store_false", dest="tiktok_auto", help="Disable TikTok auto-click")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be posted to each platform without actually posting")
    args = parser.parse_args()

    primary_modes = sum(bool(x) for x in [args.all, args.shared_one, bool(args.dir)])
    if primary_modes > 1:
        parser.error("Choose only one primary mode: --all, --shared-one, or --dir")
    if args.shared_one and not args.difficulty:
        parser.error("--shared-one requires --difficulty")
    if args.all and args.difficulty:
        parser.error("--all cannot be combined with --difficulty")
    if args.dir and args.difficulty:
        parser.error("--dir cannot be combined with --difficulty")
    if not args.difficulty and not args.all and not args.dir:
        parser.error("Specify --difficulty, --shared-one --difficulty, --all, or --dir")

    engine = get_engine()
    results: list[dict[str, Any]] = []

    if args.all:
        print("\n[Mode] multi-puzzle batch mode (--all)")
        today = datetime.now(timezone.utc).date()
        q_today = text("SELECT count(*) as cnt FROM content_puzzle WHERE DATE(published_at) = :today")
        with engine.connect() as conn:
            today_base = conn.execute(q_today, {"today": today}).fetchone().cnt
        for i, diff in enumerate(["easy", "medium", "hard", "hardest"], start=1):
            r = publish_one(engine, diff, seq_number=today_base + i)
            results.append(r)
    elif args.shared_one:
        print(f"\n[Mode] single shared puzzle mode (--shared-one, difficulty={args.difficulty})")
        r = publish_one(engine, args.difficulty)
        results.append(r)
    elif args.dir:
        print(f"\n[Mode] manual posting mode (--dir)")
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
        print(f"\n[Mode] single difficulty generation (--difficulty {args.difficulty})")
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

            # Generate captions from puzzle JSON
            puzzle_json_path = DOCS_DIR / "puzzles" / f"puzzle_{r['code']}.json"
            if puzzle_json_path.exists():
                with open(puzzle_json_path) as f:
                    pdata = json.load(f)
                removed = pdata.get("removed_pieces", [])
                diff_label = "Unknown"
                try:
                    q_diff = text("SELECT difficulty_id FROM content_puzzle WHERE code = :code LIMIT 1")
                    with engine.connect() as conn:
                        row = conn.execute(q_diff, {"code": r["code"]}).fetchone()
                    if row:
                        diff_label = _DIFFICULTY_LABELS.get(str(row.difficulty_id), "Unknown")
                except Exception:
                    pass
                write_caption(Path(r["img_dir"]), r["code"], diff_label, removed_pieces=removed)
                print(f"  [OK] caption generated (removed={removed}, difficulty={diff_label})")
            else:
                print(f"  [WARN] puzzle JSON not found, skipping caption: {puzzle_json_path}")

    # Summary
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    for r in results:
        print(f"  {r['code']:10s} [{r['difficulty']:6s}] {r['puzzle_name']}  removed={r['removed']}")
        print(f"             {r['url']}")
    print("=" * 60)

    # Write Reel queue for scheduled posting (run_reel_publish.bat, ~20 min later)
    if not args.dir:
        tmp_dir = PROJECT_ROOT / "tmp"
        tmp_dir.mkdir(exist_ok=True)
        reel_queue_path = tmp_dir / "reel_queue.txt"
        with open(reel_queue_path, "w", encoding="utf-8") as f:
            for r in results:
                f.write(r["code"] + "\n")
        print(f"\n  [Reel Queue] Written: {reel_queue_path}")
        print(f"  Run run_reel_publish.bat in ~20 minutes to post Reels with cover images.")

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

    # Twitter (X) publish — rotation-aware via auto_post_x_daily.py
    if args.twitter:
        date_str = Path(results[0]["img_dir"]).parent.name
        print(f"\n  [Twitter/X] {'[DryRun] ' if args.dry_run else ''}Posting via auto_post_x_daily.py (date={date_str}) ...")
        
        # Check for pre-existing session error flag
        _twitter_session_flag = PROJECT_ROOT / "scripts" / "logs" / "twitter_session_error.flag"
        if _twitter_session_flag.exists():
            print(f"  [Twitter/X] ERROR: Session is flagged as expired. Please refresh x_cookies.json.")
            _append_twitter_log("ALL", "error:session_expired")
        else:
            cmd = ["poetry", "run", "python", "scripts/auto_post_x_daily.py", "--date", date_str]
            if args.dry_run:
                cmd.append("--dry-run")
            
            _proc = _sp.run(cmd, cwd=str(PROJECT_ROOT), check=False)
            if _proc.returncode == 0:
                # Success! Clear flags if they exist
                _nr_flag = PROJECT_ROOT / "scripts" / "logs" / "twitter_no_confirm.flag"
                for f in [_twitter_session_flag, _nr_flag]:
                    if f.exists():
                        f.unlink()
            else:
                # Check if it was a session error during this run
                if _twitter_session_flag.exists():
                    print(f"  [Twitter/X] ERROR: Session expired during post. Please refresh x_cookies.json.")
                    _append_twitter_log("ALL", "error:session_expired")
                else:
                    print(f"  [Twitter/X] ERROR: auto_post_x_daily.py failed (exit={_proc.returncode})")
                    _append_twitter_log("ALL", f"error:exit({_proc.returncode})")

    # Instagram publish
    if args.instagram:
        if args.dry_run:
            print("\n  [Instagram][DryRun] Would post carousel for:")
            for r in results:
                img_dir = Path(r["img_dir"])
                caption_path = next((img_dir / f for f in ["caption_instagram.txt", "caption.txt"] if (img_dir / f).exists()), None)
                print(f"    {r['code']}: layer.png + answer_3d_x.png + answer_3d_y.png | caption={caption_path.name if caption_path else 'none'}")
        else:
            print("\n  Posting to Instagram...")
            pending_instagram = []
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
                        ig_cmd = ["poetry", "run", "python", "scripts/publish_instagram.py",
                                  "--dir", r["img_dir"], "--base-url", PAGES_BASE_URL]
                        if args.also_reel:
                            ig_cmd.append("--also-reel")
                        _sp.run(ig_cmd, check=True, cwd=str(PROJECT_ROOT))
                    except Exception as e:
                        print(f"  [WARN] Instagram post failed for {r['code']}: {e}")
                else:
                    print(f"  [WARN] Media not live yet for {r['code']}. Deferring Instagram post to retry pass.")
                    pending_instagram.append(r)

            if pending_instagram:
                print("\n  [Instagram] Retry pass for delayed GitHub Pages propagation...")
                for r in pending_instagram:
                    print(f"  [IG] Retry: {r['code']} ...")
                    asset_url = f"{PAGES_BASE_URL}/images/{r['code'].replace('_', '/')}/layer.png"
                    try:
                        with urllib.request.urlopen(asset_url) as response:
                            if response.getcode() == 200:
                                ig_cmd = ["poetry", "run", "python", "scripts/publish_instagram.py",
                                          "--dir", r["img_dir"], "--base-url", PAGES_BASE_URL]
                                if args.also_reel:
                                    ig_cmd.append("--also-reel")
                                _sp.run(ig_cmd, check=True, cwd=str(PROJECT_ROOT))
                                continue
                    except (urllib.error.HTTPError, urllib.error.URLError):
                        pass
                    except Exception as e:
                        print(f"  [WARN] Instagram retry failed for {r['code']}: {e}")
                        continue

                    print(f"  [ERROR] Media did not become live in time. Skipping Instagram post for {r['code']}.")

    # TikTok publish (browser automation)
    # Strategy: TikTok → Discovery — short cut (0-8s), no answer, hook-first
    if args.tiktok:
        _hook_cfg = load_hook_config()
        _hook = _hook_cfg["hook_pattern"]
        if args.dry_run:
            print(f"\n  [TikTok][DryRun] Would post (hook={_hook}) for:")
            for r in results:
                sns_dir = PROJECT_ROOT / "docs" / "sns_videos"
                video_candidates = [sns_dir / f"{r['code']}_tiktok_A.mp4", sns_dir / f"{r['code']}_tiktok.mp4", sns_dir / f"{r['code']}_teaser.mp4"]
                video_path = next((p for p in video_candidates if p.exists()), None)
                img_dir = Path(r["img_dir"])
                caption_path = next((img_dir / f for f in ["caption_tiktok.txt", "caption.txt"] if (img_dir / f).exists()), None)
                print(f"    {r['code']}: video={video_path.name if video_path else 'none'} | caption={caption_path.name if caption_path else 'none'}")
        else:
            print(f"\n  [TikTok] Preparing posts (hook={_hook}, browser automation)...")
            
            # Check for pre-existing session error flag
            _tiktok_session_flag = PROJECT_ROOT / "scripts" / "logs" / "tiktok_session_error.flag"
            if _tiktok_session_flag.exists():
                print(f"  [TikTok] ERROR: Session is flagged as expired. Please refresh tiktok_cookies.json.")
                # We don't skip the whole loop because maybe some succeed or the user fixes it? 
                # Actually, browser automation will fail anyway. Let's warn and continue (it will hit the error check inside the loop).
            
            for r in results:
                sns_dir = PROJECT_ROOT / "docs" / "sns_videos"
                # Pattern A: _tiktok_A.mp4 (drawtext overlay) must be first to guarantee
                #            the text overlay is actually posted. _teaser.mp4 has no overlay
                #            and must NOT precede _tiktok_A.mp4 when hook == "A".
                # Pattern B: _teaser.mp4 preferred (existing behavior, no text overlay).
                if _hook == "A":
                    video_candidates = [
                        sns_dir / f"{r['code']}_tiktok_A.mp4",  # required: drawtext overlay
                        sns_dir / f"{r['code']}_tiktok.mp4",    # preferred fallback: updated TikTok export
                        sns_dir / f"{r['code']}_teaser.mp4",    # older fallback: no overlay (logged as warn)
                        sns_dir / f"{r['code']}_full.mp4",
                        sns_dir / f"{r['code']}.mp4",
                    ]
                else:
                    video_candidates = [
                        sns_dir / f"{r['code']}_tiktok.mp4",
                        sns_dir / f"{r['code']}_teaser.mp4",
                        sns_dir / f"{r['code']}_full.mp4",
                        sns_dir / f"{r['code']}.mp4",
                    ]
                video_path = next((p for p in video_candidates if p.exists()), None)

                img_dir = Path(r["img_dir"])
                caption_candidates = [
                    img_dir / "caption_tiktok.txt",
                    img_dir / "caption.txt",
                ]
                caption_path = next((p for p in caption_candidates if p.exists()), None)

                if video_path is None:
                    print(f"  [TikTok] ERROR: No video found for {r['code']} — skipping.")
                    print(f"           Searched: {[str(c) for c in video_candidates]}")
                    _append_hook_log(r["code"], _hook, "", "error: no video")
                    continue
                if caption_path is None:
                    print(f"  [TikTok] ERROR: No caption found for {r['code']} — skipping.")
                    _append_hook_log(r["code"], _hook, video_path.name, "error: no caption")
                    continue

                print(f"  [TikTok] {r['code']} → {video_path.name}")

                # MO-2: Detect Pattern A fallback — A intended but _tiktok_A.mp4 not used.
                # This means text overlay is absent; post must be excluded from A/B analysis.
                a_fallback = _hook == "A" and video_path.name != f"{r['code']}_tiktok_A.mp4"
                if a_fallback:
                    print(f"  [TikTok] WARN: hook=A but posting {video_path.name} (no text overlay).")
                    print(f"  [TikTok] WARN: _tiktok_A.mp4 was not generated. Check ffmpeg drawtext.")
                    print(f"  [TikTok] WARN: This post must be EXCLUDED from A/B analysis.")

                # Build subprocess command
                # --cover: use 3d_x.png as TikTok cover image if available
                cover_path = Path(r["img_dir"]) / "3d_x.png"
                tiktok_cmd = [
                    "poetry", "run", "python",
                    "scripts/publish_tiktok_browser.py",
                    "--video", str(video_path),
                    "--caption", str(caption_path),
                ]
                if cover_path.exists():
                    tiktok_cmd += ["--cover", str(cover_path)]
                if args.tiktok_auto:
                    tiktok_cmd.append("--auto")
                    print(f"  [TikTok] Mode: auto (--tiktok-auto)")
                else:
                    print(f"  [TikTok] Mode: semi-auto (manual Post click required)")

                status = "ok"
                try:
                    _sp.run(tiktok_cmd, check=True, cwd=str(PROJECT_ROOT))
                except Exception as e:
                    # Distinguish failure causes via flag files written by publish_tiktok_browser.py
                    _session_flag = PROJECT_ROOT / "scripts" / "logs" / "tiktok_session_error.flag"
                    _redirect_flag = PROJECT_ROOT / "scripts" / "logs" / "tiktok_no_redirect.flag"
                    if _session_flag.exists():
                        status = "error:session_expired"
                        _session_flag.unlink()
                        print(f"  [TikTok] ERROR: Session expired for {r['code']}. Refresh tiktok_cookies.json.")
                    elif _redirect_flag.exists():
                        status = "warn:post_no_redirect"
                        _redirect_flag.unlink()
                        print(f"  [TikTok] WARN: {r['code']} — post clicked but page did not redirect. Check TikTok Studio.")
                    else:
                        status = f"warn:{e}"
                        print(f"  [TikTok] WARN: Post failed for {r['code']}: {e}")
                # Append Pattern A fallback marker so contaminated posts are identifiable in CSV
                if a_fallback:
                    status = f"warn:A_fallback({video_path.name})" if status == "ok" else f"{status}+A_fallback"
                _append_hook_log(r["code"], _hook, video_path.name, status)

    # Instagram Reel publish
    # Strategy: Instagram Reel → Brand exposure — full video (0-12s) with answer
    if args.instagram_reel:
        if args.dry_run:
            print("\n  [Instagram Reel][DryRun] Would post Reels for:")
            for r in results:
                sns_dir = PROJECT_ROOT / "docs" / "sns_videos"
                video_candidates = [sns_dir / f"{r['code']}_instagram.mp4", sns_dir / f"{r['code']}_full.mp4"]
                video_path = next((p for p in video_candidates if p.exists()), None)
                img_dir = Path(r["img_dir"])
                caption_path = next((img_dir / f for f in ["caption_instagram.txt", "caption.txt"] if (img_dir / f).exists()), None)
                print(f"    {r['code']}: video={video_path.name if video_path else 'none'} | cover=3d_x.png | caption={caption_path.name if caption_path else 'none'}")
        else:
            print("\n  [Instagram Reel] Posting Reels...")
            for r in results:
                img_dir = Path(r["img_dir"])
                print(f"  [Instagram Reel] {r['code']} ...")

                # Wait for cover image (3d_x.png) to be live on GitHub Pages
                # before posting, so Instagram API can fetch it.
                cover_asset_url = (
                    f"{PAGES_BASE_URL}/images/{r['code'].replace('_', '/')}/3d_x.png"
                )
                max_retries = 15
                retry_wait = 20  # seconds
                is_live = False
                for attempt in range(1, max_retries + 1):
                    try:
                        with urllib.request.urlopen(cover_asset_url) as response:
                            if response.getcode() == 200:
                                print(f"    [OK] Cover image is live! (Attempt {attempt})")
                                is_live = True
                                break
                    except (urllib.error.HTTPError, urllib.error.URLError):
                        pass
                    print(f"    [...] Waiting for GitHub Pages... (Attempt {attempt}/{max_retries})")
                    time.sleep(retry_wait)

                if not is_live:
                    print(f"  [Instagram Reel] ERROR: Cover image did not become live in time. Skipping {r['code']}.")
                    continue

                try:
                    _sp.run(
                        [
                            "poetry", "run", "python",
                            "scripts/publish_instagram_reel.py",
                            "--puzzle-id", r["code"],
                            "--dir", str(img_dir),
                            "--base-url", PAGES_BASE_URL,
                        ],
                        check=True,
                        cwd=str(PROJECT_ROOT),
                    )
                except Exception as e:
                    print(f"  [Instagram Reel] WARN: Post failed for {r['code']}: {e}")

    # Instagram Carousel publish
    # Strategy: Instagram Carousel → Puzzle catalog (layer.png = catalog cover)
    if args.instagram_carousel:
        print("\n  [Instagram Carousel] Posting catalogs...")
        for r in results:
            img_dir = Path(r["img_dir"])
            print(f"  [Instagram Carousel] {r['code']} ...")
            try:
                _sp.run(
                    [
                        "poetry", "run", "python",
                        "scripts/publish_instagram_carousel.py",
                        "--dir", str(img_dir),
                        "--base-url", PAGES_BASE_URL,
                    ],
                    check=True,
                    cwd=str(PROJECT_ROOT),
                )
            except Exception as e:
                print(f"  [Instagram Carousel] WARN: Post failed for {r['code']}: {e}")

    print("=" * 60)


if __name__ == "__main__":
    main()
