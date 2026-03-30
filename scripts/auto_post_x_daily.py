#!/usr/bin/env python3
"""
Auto-post daily puzzles to X (Twitter) with P-A/P-C/P-B rotation.

Usage:
  # Post today's 4 puzzles
  python scripts/auto_post_x_daily.py

  # Dry-run (show what would be posted, no actual posting)
  python scripts/auto_post_x_daily.py --dry-run

  # Target a specific date's puzzles
  python scripts/auto_post_x_daily.py --date 20260318 --dry-run

  # Re-run today (skips already-posted puzzles)
  python scripts/auto_post_x_daily.py --force
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCS_IMAGES = PROJECT_ROOT / "docs" / "images"
STATE_FILE = Path(__file__).resolve().parent / "x_post_state.json"
SHARE_BASE = "https://souchi-lab.github.io/sochi-blocks/share"

# ---------------------------------------------------------------------------
# Pattern matrix: cycle_day -> difficulty -> pattern
# ---------------------------------------------------------------------------
PATTERN_MATRIX: dict[int, dict[str, str]] = {
    0: {"Easy": "P-A", "Medium": "P-C", "Hard": "P-B", "Hardest": "P-A"},
    1: {"Easy": "P-C", "Medium": "P-B", "Hard": "P-A", "Hardest": "P-C"},
    2: {"Easy": "P-B", "Medium": "P-A", "Hard": "P-C", "Hardest": "P-B"},
}

DIFFICULTY_ORDER = ["Easy", "Medium", "Hard", "Hardest"]

HOOK: dict[str, str] = {
    "Easy":    "このブロック、どこに置く？ 🧩",
    "Medium":  "30秒で解けたら天才！ 🧩",
    "Hard":    "解ける？難問です 🧩",
    "Hardest": "上位数%だけ解ける難問 🧩",
}

PC_DESC: dict[str, str] = {
    "Easy":    "🧩 Easy パズルに挑戦！",
    "Medium":  "🧩 Medium パズルに挑戦！",
    "Hard":    "🧩 Hard パズルに挑戦！",
    "Hardest": "🧩 上級パズルに挑戦！",
}

HASHTAGS: dict[str, str] = {
    "Easy":    "#SoChiBlocks #ブロックパズル #論理パズル #脳トレ",
    "Medium":  "#SoChiBlocks #ブロックパズル #論理パズル #脳トレ",
    "Hard":    "#SoChiBlocks #ブロックパズル #論理パズル #難問",
    "Hardest": "#SoChiBlocks #ブロックパズル #論理パズル #難問",
}

# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------

def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"cycle_day": 0, "last_run_date": "", "posted_today": []}


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

# ---------------------------------------------------------------------------
# Puzzle discovery
# ---------------------------------------------------------------------------

def find_puzzles(date_str: str) -> dict[str, Path]:
    """
    Scan docs/images/YYYYMMDD/ and return {difficulty: puzzle_dir}.
    If multiple dirs share a difficulty, the one with the smallest sequence number wins.
    Exits with error if not all 4 difficulties are found.
    """
    img_dir = DOCS_IMAGES / date_str
    if not img_dir.exists():
        print(f"[Error] Directory not found: {img_dir}", file=sys.stderr)
        sys.exit(1)

    found: dict[str, Path] = {}
    for d in sorted(img_dir.iterdir()):
        if not d.is_dir():
            continue
        caption_file = d / "caption.txt"
        if not caption_file.exists():
            continue
        difficulty = _read_difficulty(caption_file)
        if difficulty and difficulty not in found:
            found[difficulty] = d

    missing = [diff for diff in DIFFICULTY_ORDER if diff not in found]
    if missing:
        print(f"[Error] Missing difficulties for {date_str}: {missing}", file=sys.stderr)
        sys.exit(1)

    return found


def _read_difficulty(caption_file: Path) -> str | None:
    for line in caption_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("Difficulty:"):
            return line.split(":", 1)[1].strip()
    return None


def _puzzle_id(date_str: str, puzzle_dir: Path) -> str:
    return f"{date_str}_{puzzle_dir.name}"

# ---------------------------------------------------------------------------
# Caption / reply generation
# ---------------------------------------------------------------------------

def share_url(puzzle_id: str) -> str:
    return f"{SHARE_BASE}/{puzzle_id}.html"


def generate_captions(puzzle_dir: Path, puzzle_id: str, difficulty: str, pattern: str) -> None:
    """Overwrite caption and reply files for the given pattern."""
    tags = HASHTAGS[difficulty]
    url = share_url(puzzle_id)

    if pattern == "P-A":
        caption = f"{HOOK[difficulty]}\n\n{tags}"
        (puzzle_dir / "caption_twitter.txt").write_text(caption, encoding="utf-8")
    elif pattern == "P-C":
        caption = f"{PC_DESC[difficulty]}\n\n{tags}"
        (puzzle_dir / "caption_twitter_pc.txt").write_text(caption, encoding="utf-8")
    elif pattern == "P-B":
        caption = f"{HOOK[difficulty]}\n\n▶ {url}\n{tags}"
        (puzzle_dir / "caption_twitter_pb.txt").write_text(caption, encoding="utf-8")

    # reply1 (shared)
    (puzzle_dir / "reply1.txt").write_text("✅ 正解はこちら！", encoding="utf-8")

    # reply2
    if pattern in ("P-A", "P-C"):
        reply2 = f"もっと遊ぶ → {url}\n\n全レベル無料 → プロフURLから\n#SoChiBlocks #ブロックパズル #論理パズル"
        (puzzle_dir / "reply2_pa.txt").write_text(reply2, encoding="utf-8")
    else:  # P-B
        reply2 = f"全レベル無料 → プロフURLから\n{tags}"
        (puzzle_dir / "reply2_pb.txt").write_text(reply2, encoding="utf-8")

# ---------------------------------------------------------------------------
# Answer image generation
# ---------------------------------------------------------------------------

def ensure_answer_images(puzzle_id: str, puzzle_dir: Path) -> None:
    x_img = puzzle_dir / "answer_3d_x.png"
    y_img = puzzle_dir / "answer_3d_y.png"
    if x_img.exists() and y_img.exists():
        return
    print(f"  [Generate] answer images for {puzzle_id} ...")
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "generate_answer_images.py"),
         "--puzzle_id", puzzle_id],
        cwd=str(PROJECT_ROOT),
    )
    if result.returncode != 0:
        print(f"[Error] Failed to generate answer images for {puzzle_id}", file=sys.stderr)
        sys.exit(1)

# ---------------------------------------------------------------------------
# Posting
# ---------------------------------------------------------------------------

CAPTION_FILE: dict[str, str] = {
    "P-A": "caption_twitter.txt",
    "P-C": "caption_twitter_pc.txt",
    "P-B": "caption_twitter_pb.txt",
}

REPLY2_FILE: dict[str, str] = {
    "P-A": "reply2_pa.txt",
    "P-C": "reply2_pa.txt",
    "P-B": "reply2_pb.txt",
}


def post_puzzle(puzzle_dir: Path, pattern: str, dry_run: bool) -> bool:
    """
    Build and run publish_twitter.py for one puzzle.
    Returns True on success, False on failure.
    """
    caption_file = puzzle_dir / CAPTION_FILE[pattern]
    reply1_file = puzzle_dir / "reply1.txt"
    reply2_file = puzzle_dir / REPLY2_FILE[pattern]
    img_x = puzzle_dir / "answer_3d_x.png"
    img_y = puzzle_dir / "answer_3d_y.png"

    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "publish_twitter.py"),
        "--dir", str(puzzle_dir),
        "--caption", str(caption_file),
        "--thread",
        "--reply", reply1_file.read_text(encoding="utf-8").strip(),
        "--reply-image", f"{img_x}:{img_y}",
        "--reply", reply2_file.read_text(encoding="utf-8").strip(),
    ]

    if dry_run:
        print(f"  [DryRun] {puzzle_dir.parent.name}/{puzzle_dir.name} ({pattern})")
        print(f"    caption : {caption_file.name}")
        print(f"    reply1  : {reply1_file.read_text(encoding='utf-8').strip()}")
        print(f"    reply-img: answer_3d_x.png + answer_3d_y.png")
        print(f"    reply2  : {reply2_file.read_text(encoding='utf-8').strip()[:60]}...")
        return True

    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT), env={**__import__('os').environ, "PYTHONUTF8": "1"})
    return result.returncode == 0

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Auto-post daily puzzles to X with P-A/P-C/P-B rotation")
    parser.add_argument("--date", default=None, help="Target date YYYYMMDD (default: today)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be posted without posting")
    parser.add_argument("--force", action="store_true", help="Skip duplicate-run check")
    args = parser.parse_args()

    today = args.date or datetime.now(timezone.utc).strftime("%Y%m%d")
    print(f"[auto_post_x_daily] date={today} dry_run={args.dry_run} force={args.force}")

    # Load state
    state = load_state()
    cycle_day = state["cycle_day"]
    last_run_date = state.get("last_run_date", "")

    # Reset posted_today when date changes
    if today != last_run_date:
        state["posted_today"] = []
        state["last_run_date"] = today

    posted_today: list[str] = state.get("posted_today", [])

    # Duplicate-run check
    if not args.force and not args.dry_run and last_run_date == today and len(posted_today) > 0:
        remaining = [p for p in posted_today]
        print(f"[Info] Already ran today ({today}). posted={posted_today}")
        print("[Info] Use --force to re-run (skips already-posted puzzles).")
        sys.exit(0)

    # Find puzzles
    puzzles = find_puzzles(today)  # {difficulty: Path}
    pattern_for = PATTERN_MATRIX[cycle_day % 3]

    print(f"\n[Cycle day {cycle_day} → pattern: {pattern_for}]")
    print(f"{'Difficulty':<12} {'Dir':<8} {'Pattern':<6} {'Status'}")
    print("-" * 50)
    for diff in DIFFICULTY_ORDER:
        d = puzzles[diff]
        pid = _puzzle_id(today, d)
        pat = pattern_for[diff]
        already = pid in posted_today
        print(f"{diff:<12} {d.name:<8} {pat:<6} {'[skip: posted]' if already else ''}")
    print()

    # Process each puzzle in difficulty order
    success_count = 0
    for diff in DIFFICULTY_ORDER:
        puzzle_dir = puzzles[diff]
        puzzle_id = _puzzle_id(today, puzzle_dir)
        pattern = pattern_for[diff]

        if puzzle_id in posted_today:
            print(f"[Skip] {puzzle_id} ({diff}) — already posted today")
            success_count += 1
            continue

        print(f"\n[Post] {puzzle_id} ({diff} / {pattern})")

        # Generate captions (always overwrite)
        generate_captions(puzzle_dir, puzzle_id, diff, pattern)

        # Ensure answer images
        if not args.dry_run:
            ensure_answer_images(puzzle_id, puzzle_dir)

        # Post
        ok = post_puzzle(puzzle_dir, pattern, dry_run=args.dry_run)

        if ok:
            if not args.dry_run:
                posted_today.append(puzzle_id)
                state["posted_today"] = posted_today
                save_state(state)
            success_count += 1
            print(f"  ✓ {puzzle_id} posted.")
        else:
            print(f"  ✗ {puzzle_id} FAILED. Stopping.", file=sys.stderr)
            break

    # Advance cycle_day when all 4 posted
    if not args.dry_run and success_count == 4 and len([p for p in posted_today if p.startswith(today)]) >= 4:
        state["cycle_day"] = (cycle_day + 1) % 3
        save_state(state)
        print(f"\n[State] All posted. cycle_day → {state['cycle_day']}")
    elif args.dry_run:
        print(f"\n[DryRun] Done. cycle_day would advance to {(cycle_day + 1) % 3} after real run.")
    else:
        print(f"\n[State] {success_count}/4 posted. cycle_day stays at {cycle_day}.")


if __name__ == "__main__":
    main()
