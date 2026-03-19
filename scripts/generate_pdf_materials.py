#!/usr/bin/env python3
"""
Generate an A4 printable PDF educational material from Instagram assets.
It creates a folding worksheet (Problem on front, Solution on back).

Usage:
  python scripts/generate_pdf_materials.py --puzzle_id 20260219_002
"""

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import qrcode

# ---------------------------------------------------------------------------
# Paths and Constants
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
INSTAGRAM_DIR = PROJECT_ROOT / "out" / "instagram"
PDF_DIR = PROJECT_ROOT / "out" / "pdf"

# A4 at 300 DPI: 2480 x 3508 pixels
A4_WIDTH = 2480
A4_HEIGHT = 3508
HALF_HEIGHT = A4_HEIGHT // 2

BG_COLOR = (250, 250, 250)
BRAND_COLOR = (30, 30, 30)
LABEL_COLOR = (100, 100, 100)


def _try_load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if bold:
        for name in ["meiryo.ttc", "msgothic.ttc", "arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"]:
            try:
                return ImageFont.truetype(name, size)
            except OSError:
                continue
    for name in ["meiryo.ttc", "msgothic.ttc", "arial.ttf", "Arial.ttf", "DejaVuSans.ttf"]:
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


def create_qr_code(url: str, size: int) -> Image.Image:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    return img.resize((size, size), Image.Resampling.LANCZOS)


def _format_difficulty(caption: str) -> str:
    lines = caption.split('\n')
    difficulty = "Medium"
    for line in lines:
        if line.startswith("Difficulty:"):
            difficulty = line.split(":")[1].strip()
            break
    
    return difficulty

def draw_top_half(
    img_draw: ImageDraw.ImageDraw, 
    canvas: Image.Image,
    puzzle_id: str, 
    caption: str, 
    url: str,
    img_layers: Image.Image,
    img_3d_x: Image.Image,
    img_3d_y: Image.Image,
    img_missing: Image.Image
):
    """Draw the Problem section on the top half of the A4 paper."""
    title_font = _try_load_font(100, bold=True)
    sub_font = _try_load_font(40, bold=True)
    label_font = _try_load_font(30)
    
    title = "SoChi BLOCKS 3D PUZZLE"
    tx, ty = _text_center(img_draw, title, title_font, A4_WIDTH // 2, 80)
    img_draw.text((tx, ty), title, fill=BRAND_COLOR, font=title_font)
    
    difficulty = _format_difficulty(caption)
    sub = f"Puzzle: {puzzle_id}  |  Difficulty: {difficulty}"
    sx, sy = _text_center(img_draw, sub, sub_font, A4_WIDTH // 2, 190)
    img_draw.text((sx, sy), sub, fill=LABEL_COLOR, font=sub_font)
    
    # --- Row 1: Layer Image ---
    target_layer_w = 1600
    img_l = img_layers.copy()
    scale_l = target_layer_w / img_l.width
    target_layer_h = int(img_l.height * scale_l)
    img_l = img_l.resize((target_layer_w, target_layer_h), Image.Resampling.LANCZOS)
    layer_x = (A4_WIDTH - target_layer_w) // 2
    layer_y = 250
    canvas.paste(img_l, (layer_x, layer_y))

    # --- Row 2: 3D Angle 1 & 2 ---
    target_3d_size = 500
    img1 = img_3d_x.copy()
    img1.thumbnail((target_3d_size, target_3d_size), Image.Resampling.LANCZOS)
    img2 = img_3d_y.copy()
    img2.thumbnail((target_3d_size, target_3d_size), Image.Resampling.LANCZOS)

    gap_3d = 100
    total_3d_w = img1.width + img2.width + gap_3d
    start_x = (A4_WIDTH - total_3d_w) // 2
    y_3d_row = layer_y + target_layer_h + 30
    
    canvas.paste(img1, (start_x, y_3d_row))
    canvas.paste(img2, (start_x + img1.width + gap_3d, y_3d_row))
    
    img_draw.text((start_x + img1.width//2 - 40, y_3d_row + target_3d_size + 10), "ANGLE 1", fill=LABEL_COLOR, font=label_font)
    img_draw.text((start_x + img1.width + gap_3d + img2.width//2 - 40, y_3d_row + target_3d_size + 10), "ANGLE 2", fill=LABEL_COLOR, font=label_font)

    # --- Row 3: Missing Pieces & QR Code ---
    # We will place them side-by-side
    target_missing_w = 1200
    img_m = img_missing.copy()
    scale_m = target_missing_w / img_m.width
    target_missing_h = int(img_m.height * scale_m)
    img_m = img_m.resize((target_missing_w, target_missing_h), Image.Resampling.LANCZOS)
    
    qr_size = 200
    qr_img = create_qr_code(url, qr_size)
    
    gap_row3 = 100
    total_row3_w = target_missing_w + qr_size + gap_row3
    row3_start_x = (A4_WIDTH - total_row3_w) // 2
    row3_y = y_3d_row + target_3d_size + 70
    
    canvas.paste(img_m, (row3_start_x, row3_y))
    canvas.paste(qr_img, (row3_start_x + target_missing_w + gap_row3, row3_y + (target_missing_h - qr_size)//2))
    
    # Label for QR
    img_draw.text((row3_start_x + target_missing_w + gap_row3 + 20, row3_y + (target_missing_h - qr_size)//2 - 40), "PLAY ONLINE", fill=BRAND_COLOR, font=label_font)

def draw_bottom_half(
    canvas: Image.Image,
    img_layers: Image.Image,
    img_3d_x: Image.Image,
    img_3d_y: Image.Image
):
    """Draw the Solution section on the bottom half, inverted by 180 degrees."""
    temp_canvas = Image.new("RGB", (A4_WIDTH, HALF_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(temp_canvas)
    
    title_font = _try_load_font(120, bold=True)
    label_font = _try_load_font(40)

    title = "SOLUTION - ALL CELLS FILLED"
    tx, ty = _text_center(draw, title, title_font, A4_WIDTH // 2, 200)
    draw.text((tx, ty), title, fill=BRAND_COLOR, font=title_font)
    
    # Layer image - Giant
    target_2d_w = 2100
    img2d = img_layers.copy()
    scale = target_2d_w / img2d.width
    target_2d_h = int(img2d.height * scale)
    img2d = img2d.resize((target_2d_w, target_2d_h), Image.Resampling.LANCZOS)
    
    x_2d = (A4_WIDTH - img2d.width) // 2
    y_2d = 400
    temp_canvas.paste(img2d, (x_2d, y_2d))
    
    # 3D Angles smaller at bottom
    target_3d_size = 450
    img1 = img_3d_x.copy()
    img1.thumbnail((target_3d_size, target_3d_size), Image.Resampling.LANCZOS)
    img2 = img_3d_y.copy()
    img2.thumbnail((target_3d_size, target_3d_size), Image.Resampling.LANCZOS)

    gap_3d = 80
    total_3d_w = img1.width + img2.width + gap_3d
    start_x = (A4_WIDTH - total_3d_w) // 2
    y_3d = y_2d + target_2d_h + 100
    
    temp_canvas.paste(img1, (start_x, y_3d))
    temp_canvas.paste(img2, (start_x + img1.width + gap_3d, y_3d))

    temp_canvas = temp_canvas.rotate(180)
    canvas.paste(temp_canvas, (0, HALF_HEIGHT))


def draw_folding_line(draw: ImageDraw.ImageDraw):
    """Draw a dotted line in the middle to indicate folding."""
    dash_length = 20
    gap = 20
    x = 0
    y = HALF_HEIGHT
    
    while x < A4_WIDTH:
        draw.line([(x, y), (x + dash_length, y)], fill=(200, 200, 200), width=3)
        x += dash_length + gap

def build_pdf(puzzle_id: str, out_path: Path):
    in_dir = INSTAGRAM_DIR / puzzle_id
    if not in_dir.exists():
        print(f"Error: Instagram assets not found for {puzzle_id}. Please run generate_instagram_images.py first.", file=sys.stderr)
        sys.exit(1)
        
    try:
        img_2d_full = Image.open(in_dir / "01_2d.png").convert("RGB")
        img_3d_x = Image.open(in_dir / "02_3d_x.png").convert("RGB")
        img_3d_y = Image.open(in_dir / "03_3d_y.png").convert("RGB")
        caption = (in_dir / "caption.txt").read_text(encoding="utf-8")
        url = (in_dir / "url.txt").read_text(encoding="utf-8").strip()
    except Exception as e:
        print(f"Error loading assets: {e}", file=sys.stderr)
        sys.exit(1)

    # Extract missing pieces card from 01_2d.png (Assuming bottom 27% approx from generate_instagram_images.py logic)
    # The instagram image is 1080x1080.
    # missing_top = int(1080 * 0.60) = 648
    # missing_card_h = int(1080 * 0.27) = 291
    # shadows add some pixels, so expand the box constraints to prevent cut-off
    missing_box = (16, 640, 1080 - 16, 648 + 291 + 16)
    img_missing = img_2d_full.crop(missing_box)
    
    # Extract the layer card area (top 10% to 58%) plus shadows
    layers_box = (16, 100, 1080 - 16, 108 + 518 + 16)
    img_layers = img_2d_full.crop(layers_box)

    # Create A4 canvas
    canvas = Image.new("RGB", (A4_WIDTH, A4_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(canvas)

    # Draw Top Half (Front - Problem)
    draw_top_half(draw, canvas, puzzle_id, caption, url, img_layers, img_3d_x, img_3d_y, img_missing)
    
    # Draw Bottom Half (Back - Solution)
    draw_bottom_half(canvas, img_layers, img_3d_x, img_3d_y)
    
    # Draw Folding Line
    draw_folding_line(draw)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, "PDF", resolution=300.0)
    print(f"PDF successfully generated at: {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate PDF printable materials from Instagram assets"
    )
    parser.add_argument("--puzzle_id", required=True, help="e.g. 20260219_002")
    parser.add_argument("--output_dir", default="out/pdf")
    args = parser.parse_args()

    puzzle_id = args.puzzle_id
    output_dir = Path(args.output_dir)
    out_path = output_dir / f"{puzzle_id}.pdf"
    
    print(f"Generating PDF for puzzle {puzzle_id} ...")
    build_pdf(puzzle_id, out_path)


if __name__ == "__main__":
    main()
