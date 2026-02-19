#!/usr/bin/env python3
"""
Generate 3 Instagram images (1080x1080) for a given puzzle:
  1) 2D layer image  (Pillow)
  2) 3D Angle X      (Playwright capture)
  3) 3D Angle Y      (Playwright capture)

Usage:
  python scripts/generate_instagram_images.py \
    --puzzle_id 5x4x3_0010 \
    --removed_pieces V,W \
    --output_dir output/instagram
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PUZZLE_DIR = PROJECT_ROOT / "frontend" / "public" / "puzzles"
COLORS_JSON = PROJECT_ROOT / "frontend" / "public" / "colors" / "piece_colors.json"
MASTER_PIECES_JSON = PROJECT_ROOT / "frontend" / "public" / "colors" / "master_pieces.json"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
IMG_SIZE = 1080
BG_COLOR = (250, 250, 250)
CARD_BG = (255, 255, 255)
CARD_RADIUS = 16
CELL_RADIUS = 6
CELL_GAP = 4
EMPTY_CELL_COLOR = (240, 240, 240)
LABEL_COLOR = (100, 100, 100)
BRAND_COLOR = (30, 30, 30)
TAGLINE_COLOR = (90, 90, 90)
DEFAULT_RGB = (204, 204, 204)
ALL_PIECES = list("FILNPTUVWXYZ")

# Shadow presets per layer (alpha, offset) — ③ depth difference
LAYER_SHADOW = [
    {"alpha": 18, "offset": 3, "y_shift": 0},   # Layer 1: lightest
    {"alpha": 28, "offset": 5, "y_shift": -2},   # Layer 2: medium
    {"alpha": 40, "offset": 7, "y_shift": -4},   # Layer 3: deepest
]

# ---------------------------------------------------------------------------
# Shared data loading
# ---------------------------------------------------------------------------

def load_piece_colors() -> dict[str, str]:
    with open(COLORS_JSON) as f:
        return json.load(f)


def load_master_pieces() -> dict[str, list[list[int]]]:
    """Load piece shapes: {piece_id: [[x,y,z], ...]}"""
    with open(MASTER_PIECES_JSON) as f:
        data = json.load(f)
    return {p["id"]: p["shape_json"] for p in data}


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = rgb
    return 0.299 * r + 0.587 * g + 0.114 * b


def contrast_color(bg_rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    return (255, 255, 255) if luminance(bg_rgb) < 160 else (30, 30, 30)


# ---------------------------------------------------------------------------
# Font helpers
# ---------------------------------------------------------------------------

def _try_load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if bold:
        for name in ["arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"]:
            try:
                return ImageFont.truetype(name, size)
            except OSError:
                continue
    for name in ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf"]:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _text_center(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    cx: int,
    cy: int,
) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    return cx - tw // 2, cy - th // 2


# ---------------------------------------------------------------------------
# ② Brand header (strengthened)
# ---------------------------------------------------------------------------

def draw_brand_header(
    draw: ImageDraw.ImageDraw,
    y_center: int,
) -> None:
    brand_font = _try_load_font(36, bold=True)
    tagline_font = _try_load_font(17, bold=False)

    # Main logo — wider letter spacing via manual spaced string
    text = "S o C h i   B L O C K S"
    x, y = _text_center(draw, text, brand_font, IMG_SIZE // 2, y_center - 18)
    draw.text((x, y), text, fill=BRAND_COLOR, font=brand_font)

    # Tagline — prominent, wide spacing
    tagline = "T H I N K   I N   3 D ."
    x2, y2 = _text_center(draw, tagline, tagline_font, IMG_SIZE // 2, y_center + 30)
    draw.text((x2, y2), tagline, fill=TAGLINE_COLOR, font=tagline_font)


# ---------------------------------------------------------------------------
# ③ Shadow with per-layer depth
# ---------------------------------------------------------------------------

def draw_rounded_rect_shadow(
    img: Image.Image,
    xy: tuple[int, int, int, int],
    radius: int,
    shadow_alpha: int = 25,
    shadow_offset: int = 4,
) -> None:
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    sx, sy, ex, ey = xy
    od.rounded_rectangle(
        [sx + shadow_offset, sy + shadow_offset, ex + shadow_offset, ey + shadow_offset],
        radius=radius,
        fill=(0, 0, 0, shadow_alpha),
    )
    img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))


# ---------------------------------------------------------------------------
# Layer card (with depth variation)
# ---------------------------------------------------------------------------

def draw_layer_card(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    card_x: int,
    card_y: int,
    card_w: int,
    card_h: int,
    cell_size: int,
    v_gap: int,
    layer_z: int,
    cols: int,
    rows: int,
    cell_map: dict[tuple[int, int, int], str],
    color_rgb: dict[str, tuple[int, int, int]],
    removed_pieces: set[str],
) -> ImageDraw.ImageDraw:
    label_font = _try_load_font(14, bold=True)
    title_h = 28
    card_inner_pad = 14

    # ③ Per-layer shadow depth
    shadow_cfg = LAYER_SHADOW[min(layer_z, len(LAYER_SHADOW) - 1)]
    actual_y = card_y + shadow_cfg["y_shift"]

    draw_rounded_rect_shadow(
        img,
        (card_x, actual_y, card_x + card_w, actual_y + card_h),
        CARD_RADIUS,
        shadow_alpha=shadow_cfg["alpha"],
        shadow_offset=shadow_cfg["offset"],
    )
    draw = ImageDraw.Draw(img)

    # Card background
    draw.rounded_rectangle(
        [card_x, actual_y, card_x + card_w, actual_y + card_h],
        radius=CARD_RADIUS,
        fill=CARD_BG,
    )

    # Title
    title = f"Layer {layer_z + 1}"
    tx, ty = _text_center(draw, title, label_font, card_x + card_w // 2, actual_y + title_h // 2 + 4)
    draw.text((tx, ty), title, fill=LABEL_COLOR, font=label_font)

    # Center grid within card content area
    total_grid_w = cols * cell_size + (cols - 1) * CELL_GAP
    total_grid_h = rows * cell_size + (rows - 1) * v_gap
    content_area_y = actual_y + title_h + card_inner_pad
    content_area_h = card_h - title_h - card_inner_pad * 2 - 8
    gx0 = card_x + (card_w - total_grid_w) // 2
    gy0 = content_area_y + (content_area_h - total_grid_h) // 2

    for row in range(rows):
        for col in range(cols):
            cx = gx0 + col * (cell_size + CELL_GAP)
            cy = gy0 + (rows - 1 - row) * (cell_size + v_gap)

            piece = cell_map.get((col, row, layer_z))
            if piece and piece not in removed_pieces:
                rgb = color_rgb.get(piece, DEFAULT_RGB)
                draw.rounded_rectangle(
                    [cx, cy, cx + cell_size, cy + cell_size],
                    radius=CELL_RADIUS,
                    fill=rgb,
                )
            else:
                draw.rounded_rectangle(
                    [cx, cy, cx + cell_size, cy + cell_size],
                    radius=CELL_RADIUS,
                    fill=EMPTY_CELL_COLOR,
                )

    return draw


# ---------------------------------------------------------------------------
# ① Missing Pieces panel — shape preview
# ---------------------------------------------------------------------------

def draw_piece_shape_mini(
    draw: ImageDraw.ImageDraw,
    origin_x: int,
    origin_y: int,
    shape: list[list[int]],
    color: tuple[int, int, int],
    mini_cell: int = 10,
    mini_gap: int = 1,
    radius: int = 2,
) -> tuple[int, int]:
    """Draw a mini 2D piece shape. Returns (total_width, total_height)."""
    # Normalize to 0-based using only x,y (ignore z for 2D preview)
    coords = [(b[0], b[1]) for b in shape]
    min_x = min(c[0] for c in coords)
    min_y = min(c[1] for c in coords)
    norm = [(c[0] - min_x, c[1] - min_y) for c in coords]
    max_x = max(c[0] for c in norm)
    max_y = max(c[1] for c in norm)

    step = mini_cell + mini_gap
    for bx, by in norm:
        rx = origin_x + bx * step
        ry = origin_y + (max_y - by) * step  # flip y
        draw.rounded_rectangle(
            [rx, ry, rx + mini_cell, ry + mini_cell],
            radius=radius,
            fill=color,
        )
    total_w = (max_x + 1) * step - mini_gap
    total_h = (max_y + 1) * step - mini_gap
    return total_w, total_h


def draw_missing_pieces_card(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    card_x: int,
    card_y: int,
    card_w: int,
    card_h: int,
    missing_pieces: list[str],
    color_rgb: dict[str, tuple[int, int, int]],
    piece_shapes: dict[str, list[list[int]]],
) -> ImageDraw.ImageDraw:
    """Draw Missing Pieces as a full-width card with shadow."""
    title_font = _try_load_font(18, bold=True)
    sub_font = _try_load_font(13)
    label_font = _try_load_font(15, bold=True)

    # Card shadow + background
    draw_rounded_rect_shadow(
        img,
        (card_x, card_y, card_x + card_w, card_y + card_h),
        CARD_RADIUS,
        shadow_alpha=22,
        shadow_offset=4,
    )
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle(
        [card_x, card_y, card_x + card_w, card_y + card_h],
        radius=CARD_RADIUS,
        fill=CARD_BG,
    )

    if not missing_pieces:
        text = "Missing Pieces:  None"
        nx, ny = _text_center(draw, text, title_font, card_x + card_w // 2, card_y + card_h // 2)
        draw.text((nx, ny), text, fill=LABEL_COLOR, font=title_font)
        return draw

    # Title
    title = "Missing Pieces"
    title_y = card_y + 18
    tx, ty = _text_center(draw, title, title_font, card_x + card_w // 2, title_y)
    draw.text((tx, ty), title, fill=BRAND_COLOR, font=title_font)

    # Subtitle
    sub = "(not used in this solution)"
    sx, sy = _text_center(draw, sub, sub_font, card_x + card_w // 2, title_y + 22)
    draw.text((sx, sy), sub, fill=(136, 136, 136), font=sub_font)

    # Draw mini shapes — adaptive size based on piece count
    n = len(missing_pieces)
    if n <= 2:
        mini_cell, mini_gap, shape_gap = 36, 4, 60
    elif n <= 4:
        mini_cell, mini_gap, shape_gap = 28, 3, 44
    elif n <= 6:
        mini_cell, mini_gap, shape_gap = 22, 3, 36
    else:
        mini_cell, mini_gap, shape_gap = 16, 2, 28

    sorted_pieces = sorted(missing_pieces)
    piece_widths: list[int] = []
    piece_heights: list[int] = []
    for pid in sorted_pieces:
        shape = piece_shapes.get(pid, [[0, 0, 0]])
        coords = [(b[0], b[1]) for b in shape]
        w = (max(c[0] for c in coords) - min(c[0] for c in coords) + 1) * (mini_cell + mini_gap) - mini_gap
        h = (max(c[1] for c in coords) - min(c[1] for c in coords) + 1) * (mini_cell + mini_gap) - mini_gap
        piece_widths.append(w)
        piece_heights.append(h)

    total_w = sum(piece_widths) + shape_gap * (len(sorted_pieces) - 1)

    # Vertically center shapes in remaining card space
    shapes_area_top = title_y + 44
    shapes_area_bottom = card_y + card_h - 8
    max_shape_h = max(piece_heights) if piece_heights else 0
    label_space = 26  # space for label below shape
    shapes_block_h = max_shape_h + label_space
    shapes_y = shapes_area_top + (shapes_area_bottom - shapes_area_top - shapes_block_h) // 2

    # If total_w exceeds card width, wrap to 2 rows
    inner_w = card_w - 32
    if total_w > inner_w and len(sorted_pieces) > 4:
        # Split into 2 rows
        mid = (len(sorted_pieces) + 1) // 2
        rows_data = [sorted_pieces[:mid], sorted_pieces[mid:]]
        row_gap = 14
        row_h = max_shape_h + label_space
        total_block_h = row_h * 2 + row_gap
        row_start_y = shapes_area_top + (shapes_area_bottom - shapes_area_top - total_block_h) // 2

        for row_idx, row_pieces in enumerate(rows_data):
            row_widths = [piece_widths[sorted_pieces.index(p)] for p in row_pieces]
            row_total_w = sum(row_widths) + shape_gap * (len(row_pieces) - 1)
            cur_x = card_x + (card_w - row_total_w) // 2
            cur_y = row_start_y + row_idx * (row_h + row_gap)

            for pid, pw in zip(row_pieces, row_widths):
                shape = piece_shapes.get(pid, [[0, 0, 0]])
                rgb = color_rgb.get(pid, DEFAULT_RGB)
                coords = [(b[0], b[1]) for b in shape]
                h = (max(c[1] for c in coords) - min(c[1] for c in coords) + 1) * (mini_cell + mini_gap) - mini_gap

                draw_piece_shape_mini(draw, cur_x, cur_y, shape, rgb, mini_cell, mini_gap, radius=3)
                lx, ly = _text_center(draw, pid, label_font, cur_x + pw // 2, cur_y + h + 12)
                draw.text((lx, ly), pid, fill=LABEL_COLOR, font=label_font)
                cur_x += pw + shape_gap
    else:
        cx_start = card_x + (card_w - total_w) // 2
        cur_x = cx_start
        for pid, pw in zip(sorted_pieces, piece_widths):
            shape = piece_shapes.get(pid, [[0, 0, 0]])
            rgb = color_rgb.get(pid, DEFAULT_RGB)
            coords = [(b[0], b[1]) for b in shape]
            h = (max(c[1] for c in coords) - min(c[1] for c in coords) + 1) * (mini_cell + mini_gap) - mini_gap

            draw_piece_shape_mini(draw, cur_x, shapes_y, shape, rgb, mini_cell, mini_gap, radius=3)
            lx, ly = _text_center(draw, pid, label_font, cur_x + pw // 2, shapes_y + h + 12)
            draw.text((lx, ly), pid, fill=LABEL_COLOR, font=label_font)
            cur_x += pw + shape_gap

    return draw


# ---------------------------------------------------------------------------
# 2D Layer Image — main generator
# ---------------------------------------------------------------------------

def generate_layer_image(
    puzzle_path: Path,
    colors: dict[str, str],
    removed_pieces: set[str],
    output_path: Path,
    piece_shapes: dict[str, list[list[int]]],
) -> None:
    with open(puzzle_path) as f:
        puzzle = json.load(f)

    grid = puzzle["grid"]
    cells = puzzle["cells"]
    n_layers = grid["z"]
    cols, rows = grid["x"], grid["y"]

    # Build lookup
    cell_map: dict[tuple[int, int, int], str] = {}
    used_pieces: set[str] = set()
    for c in cells:
        cell_map[(c["x"], c["y"], c["z"])] = c["piece"]
        if c["piece"] not in removed_pieces:
            used_pieces.add(c["piece"])

    missing_pieces = [p for p in ALL_PIECES if p not in used_pieces]
    color_rgb = {pid: hex_to_rgb(h) for pid, h in colors.items()}

    img = Image.new("RGB", (IMG_SIZE, IMG_SIZE), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # --- Layout zones (percentage-based) ---
    # Header 9%, gap 1%, Layers 48%, gap 1.5%, Missing 27%, bottom 13.5%
    side_pad = 24
    card_gap = 12
    card_inner_pad = 14

    header_h = int(IMG_SIZE * 0.09)        # ~97px
    cards_top = int(IMG_SIZE * 0.10)        # layers start
    card_h = int(IMG_SIZE * 0.48)           # ~518px for layer cards
    missing_top = int(IMG_SIZE * 0.60)      # missing starts
    missing_card_h = int(IMG_SIZE * 0.27)   # ~291px for missing card

    # 1) Brand header
    draw_brand_header(draw, header_h // 2)

    # 2) Layer cards
    available_w = IMG_SIZE - side_pad * 2
    card_w = (available_w - card_gap * (n_layers - 1)) // n_layers
    cell_size = (card_w - card_inner_pad * 2 - CELL_GAP * (cols - 1)) // cols
    v_gap = CELL_GAP

    for i in range(n_layers):
        card_x = side_pad + i * (card_w + card_gap)
        draw = draw_layer_card(
            img, draw, card_x, cards_top, card_w, card_h,
            cell_size=cell_size,
            v_gap=v_gap,
            layer_z=i,
            cols=cols, rows=rows,
            cell_map=cell_map,
            color_rgb=color_rgb,
            removed_pieces=removed_pieces,
        )

    # 3) Missing Pieces card — full width
    missing_zone_top = missing_top

    draw = ImageDraw.Draw(img)
    draw = draw_missing_pieces_card(
        img, draw,
        card_x=side_pad,
        card_y=missing_zone_top,
        card_w=IMG_SIZE - side_pad * 2,
        card_h=missing_card_h,
        missing_pieces=missing_pieces,
        color_rgb=color_rgb,
        piece_shapes=piece_shapes,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, quality=95)
    print(f"  -> {output_path}")


# ---------------------------------------------------------------------------
# 3D Capture (Playwright)
# ---------------------------------------------------------------------------
DEV_SERVER_URL = "http://localhost:5173"


def wait_for_dev_server(url: str, timeout: int = 15) -> bool:
    import urllib.request
    import urllib.error

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except (urllib.error.URLError, OSError):
            time.sleep(0.5)
    return False


def capture_3d_images(
    puzzle_id: str,
    removed_pieces_str: str,
    output_dir: Path,
) -> None:
    server_proc = None
    if not wait_for_dev_server(DEV_SERVER_URL, timeout=2):
        print("  Starting Vite dev server ...")
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

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1080, "height": 1080})

            for angle, suffix in [("x", "3d_x"), ("y", "3d_y")]:
                url = (
                    f"{DEV_SERVER_URL}/"
                    f"?puzzle_id={puzzle_id}"
                    f"&mode=capture"
                    f"&angle={angle}"
                )
                if removed_pieces_str:
                    url += f"&removed_pieces={removed_pieces_str}"

                page.goto(url)
                page.wait_for_function(
                    "window.__CAPTURE_READY__ === true",
                    timeout=15000,
                )
                page.wait_for_timeout(300)

                out_path = output_dir / f"{puzzle_id}_{suffix}.png"
                page.screenshot(path=str(out_path))
                print(f"  -> {out_path}")

            browser.close()
    finally:
        if server_proc:
            server_proc.terminate()
            print("  Dev server stopped.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Instagram images for a SoChi BLOCKS puzzle"
    )
    parser.add_argument("--puzzle_id", required=True, help="e.g. 5x4x3_0010")
    parser.add_argument("--removed_pieces", default="", help="e.g. V,W")
    parser.add_argument("--output_dir", default="output/instagram")
    args = parser.parse_args()

    puzzle_id: str = args.puzzle_id
    removed_pieces_str: str = args.removed_pieces
    removed_set = (
        {s.strip() for s in removed_pieces_str.split(",") if s.strip()}
        if removed_pieces_str
        else set()
    )
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    puzzle_path = PUZZLE_DIR / f"puzzle_{puzzle_id}.json"
    if not puzzle_path.exists():
        print(f"ERROR: Puzzle file not found: {puzzle_path}", file=sys.stderr)
        sys.exit(1)

    colors = load_piece_colors()
    piece_shapes = load_master_pieces()

    print(f"Generating images for puzzle {puzzle_id} ...")

    # 1) 2D Layer image
    print("[1/3] 2D Layer image")
    generate_layer_image(
        puzzle_path, colors, removed_set, output_dir / f"{puzzle_id}_layer.png",
        piece_shapes,
    )

    # 2-3) 3D captures
    print("[2/3] 3D Angle X")
    print("[3/3] 3D Angle Y")
    capture_3d_images(puzzle_id, removed_pieces_str, output_dir)

    print("Done!")


if __name__ == "__main__":
    main()
