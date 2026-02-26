
import json
import argparse
import os
import base64 # Import base64
from io import BytesIO # Import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, A5, landscape
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from backend.utils.qr_code_generator import generate_puzzle_qr_code # Import QR code generator

# Register Japanese font
try:
    # Assuming NotoSansCJKjp-Regular.ttf is available in the system fonts or a known path
    # For Debian/Ubuntu, fonts-noto-cjk installs them to /usr/share/fonts/opentype/noto/
    # We need to find the exact path or ensure reportlab can find it.
    # A more robust solution might involve copying the font file to a known location.
    FONT_PATH_GOTHIC = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"
    FONT_NAME_GOTHIC = "IPAGothic"
    pdfmetrics.registerFont(TTFont(FONT_NAME_GOTHIC, FONT_PATH_GOTHIC))
    FONT_NAME_JP = FONT_NAME_GOTHIC
except Exception as e:
    print(f"Warning: NotoSansCJKjp-Regular.otf not found or could not be registered: {e}. Falling back to Helvetica.")
    FONT_NAME_JP = "Helvetica"

# --- Constants ---

# Page settings
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 36

# Grid settings
CELL_SIZE = 29
GRID_COLS = 5
GRID_ROWS = 4
GRID_WIDTH = GRID_COLS * CELL_SIZE
GRID_HEIGHT = GRID_ROWS * CELL_SIZE
LAYER_SPACING = 40 # Vertical space between grids

# Font settings
FONT_NAME_EN = FONT_NAME_JP # Use Japanese font for all text for simplicity
FONT_H1 = 16
FONT_H2 = 12
FONT_BODY = 10
FONT_PIECE_SYMBOL = 15
FONT_DOT = 13

# Output directory
OUTPUT_DIR = "output/pdfs"
INTER_GRID_HORIZONTAL_SPACING = 40 # Horizontal space between grids
HEADER_PIECE_CELL_SIZE = 8 # Smaller cell size for pieces in header
HEADER_PIECE_SPACING = 5 # Spacing between piece shapes in header
QR_CODE_BASE_URL = "http://localhost:8080/viewer" # Base URL for the 3D viewer

# --- Drawing Functions ---

def draw_piece_shape(c, x_origin, y_origin, piece_shape_json, cell_size, fill_color, stroke_color=colors.black):
    """Draws a 2D representation of a piece shape."""
    min_x = min(block[0] for block in piece_shape_json)
    min_y = min(block[1] for block in piece_shape_json)

    c.setFillColor(fill_color)
    c.setStrokeColor(stroke_color)
    c.setLineWidth(0.5)

    for block in piece_shape_json:
        # Adjust coordinates to be relative to the piece's own origin (min_x, min_y)
        block_x = block[0] - min_x
        block_y = block[1] - min_y
        
        c.rect(x_origin + block_x * cell_size, y_origin + block_y * cell_size, cell_size, cell_size, fill=1, stroke=1)

def draw_header(c, page_width, page_height, puzzle_id, removed_piece_ids, master_pieces, piece_colors):
    """Draws the header section."""
    c.setFont(FONT_NAME_EN, FONT_H1)
    c.drawString(MARGIN, page_height - MARGIN, "SoChi BLOCKS Puzzle") # Placeholder Title
    
    c.setFont(FONT_NAME_EN, FONT_BODY)
    c.drawString(MARGIN, page_height - MARGIN - 20, f"Puzzle ID: {puzzle_id}")
    
    # Draw missing piece shapes
    current_x = MARGIN
    current_y = page_height - MARGIN - 60 # Adjusted vertical position for shapes
    c.setFont(FONT_NAME_EN, FONT_BODY)
    c.drawString(current_x, current_y + 10, "Missing Pieces:")
    current_x += c.stringWidth("Missing Pieces:") + HEADER_PIECE_SPACING

    for piece_id in sorted(list(removed_piece_ids)):
        piece_data = master_pieces.get(piece_id)
        if piece_data and 'shape_json' in piece_data:
            shape_json = piece_data['shape_json']
            fill_color = piece_colors.get(piece_id, colors.white)
            
            # Find max dimensions of the piece to calculate its drawn height
            max_x = max(block[0] for block in shape_json)
            min_x = min(block[0] for block in shape_json)
            max_y = max(block[1] for block in shape_json)
            min_y = min(block[1] for block in shape_json)
            
            piece_width_blocks = max_x - min_x + 1
            piece_height_blocks = max_y - min_y + 1
            
            # Draw piece shape
            draw_piece_shape(c, current_x, current_y, shape_json, HEADER_PIECE_CELL_SIZE, fill_color)
            
            # Move x for next piece
            current_x += piece_width_blocks * HEADER_PIECE_CELL_SIZE + HEADER_PIECE_SPACING


def draw_footer(c, page_width, page_height, removed_piece_ids, qr_code_b64):
    """Draws the footer and legend."""
    # Footer is now empty as per user request, but will contain QR code
    
    # Draw QR code
    if qr_code_b64:
        try:
            qr_image_data = base64.b64decode(qr_code_b64)
            qr_image = ImageReader(BytesIO(qr_image_data))
            qr_size = 50 # Size of the QR code image
            
            # Position QR code in the bottom center, above the margin
            qr_x = (page_width - qr_size) / 2
            qr_y = MARGIN
            
            c.drawImage(qr_image, qr_x, qr_y, width=qr_size, height=qr_size)
        except Exception as e:
            print(f"Error drawing QR code in footer: {e}")

def draw_layer_grid(c, x_start, y_start, layer_z, layer_label, puzzle_cells, master_pieces, piece_colors, removed_piece_ids):
    """Draws a single layer grid with its contents."""
    # Draw layer label
    c.setFillColor(colors.black) # Ensure label is black
    c.setFont(FONT_NAME_EN, FONT_H2)
    c.drawString(x_start, y_start + GRID_HEIGHT + 10, layer_label)

    # Draw cells
    for y_idx in range(GRID_ROWS):
        for x_idx in range(GRID_COLS):
            cell_x = x_start + x_idx * CELL_SIZE
            cell_y = y_start + y_idx * CELL_SIZE
            
            coord = (x_idx, y_idx, layer_z)
            
            # Draw cell background and content
            if coord in puzzle_cells and puzzle_cells[coord] not in removed_piece_ids:
                # Hint Cell
                piece_id = puzzle_cells[coord]
                piece_symbol = master_pieces.get(piece_id, {}).get('symbol', '')
                piece_color = piece_colors.get(piece_id, colors.white)
                
                c.setFillColor(piece_color)
                c.rect(cell_x, cell_y, CELL_SIZE, CELL_SIZE, fill=1, stroke=0)
                
                if piece_symbol: # Only draw symbol if it exists
                    c.setFillColor(colors.black)
                    c.setFont(FONT_NAME_EN, FONT_PIECE_SYMBOL)
                    c.drawCentredString(cell_x + CELL_SIZE / 2, cell_y + (CELL_SIZE - FONT_PIECE_SYMBOL) / 2 + 1, piece_symbol)
            else:
                # Empty or Missing Cell (display nothing)
                c.setFillColor(colors.white)
                c.rect(cell_x, cell_y, CELL_SIZE, CELL_SIZE, fill=1, stroke=0)

    # Draw grid lines on top
    c.setStrokeColor(colors.black)
    c.grid([x_start + i * CELL_SIZE for i in range(GRID_COLS + 1)], 
           [y_start + i * CELL_SIZE for i in range(GRID_ROWS + 1)])

# --- Main PDF Generation Logic ---

def load_colors_from_json(colors_path):
    """Loads color strings from JSON and maps them to reportlab color objects."""
    with open(colors_path, 'r') as f:
        color_names = json.load(f)
    
    piece_colors = {}
    for piece_id, color_name in color_names.items():
        try:
            piece_colors[piece_id] = getattr(colors, color_name)
        except AttributeError:
            print(f"Warning: Color '{color_name}' not found in reportlab.lib.colors. Defaulting to black.")
            piece_colors[piece_id] = colors.black
    return piece_colors

def get_puzzle_data(puzzle_path):
    """Loads the puzzle data from a JSON file."""
    with open(puzzle_path, 'r') as f:
        return json.load(f)

def get_master_pieces(master_pieces_path):
    """Loads the master pieces data from a JSON file."""
    with open(master_pieces_path, 'r') as f:
        return {piece['id']: piece for piece in json.load(f)}

def generate_pdf(puzzle_path, master_pieces_path, colors_path, removed_pieces_str):
    """Generates a puzzle PDF from the given data."""
    # --- 1. Data Loading & Preparation ---
    puzzle_data = get_puzzle_data(puzzle_path)
    master_pieces = get_master_pieces(master_pieces_path)
    piece_colors = load_colors_from_json(colors_path)
    removed_piece_ids = set(removed_pieces_str.split(',')) if removed_pieces_str and removed_pieces_str.strip() else set()

    puzzle_cells = {(cell['x'], cell['y'], cell['z']): cell['piece'] for cell in puzzle_data['cells']}
    puzzle_id = puzzle_data.get('puzzle_id') or puzzle_data.get('id', 'unknown_puzzle')

    # Generate QR code
    qr_code_b64 = generate_puzzle_qr_code(puzzle_id, removed_pieces_str, QR_CODE_BASE_URL)
    
    # Use BytesIO to capture PDF content in memory
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    
    # Update PAGE_WIDTH and PAGE_HEIGHT for A4 portrait orientation
    PAGE_WIDTH, PAGE_HEIGHT = A4
    
    # Calculate layout for 3 horizontal grids
    total_grids_width = (GRID_WIDTH * 3) + (INTER_GRID_HORIZONTAL_SPACING * 2)
    x_start_all_grids = (PAGE_WIDTH - total_grids_width) / 2
    
    # Position grids vertically centered, below header
    y_start_grids = (PAGE_HEIGHT - GRID_HEIGHT) / 2 - 30 # Adjusted for header and footer space

    # --- 3. Drawing ---
    draw_header(c, PAGE_WIDTH, PAGE_HEIGHT, puzzle_id, removed_piece_ids, master_pieces, piece_colors)

    layer_definitions = [
        {"z": 0, "label": "Layer 1 (Bottom)"},
        {"z": 1, "label": "Layer 2 (Middle)"},
        {"z": 2, "label": "Layer 3 (Top)"},
    ]

    for i, layer_def in enumerate(layer_definitions):
        x_pos = x_start_all_grids + i * (GRID_WIDTH + INTER_GRID_HORIZONTAL_SPACING)
        draw_layer_grid(c, x_pos, y_start_grids, layer_def["z"], layer_def["label"], 
                        puzzle_cells, master_pieces, piece_colors, removed_piece_ids)

    draw_footer(c, PAGE_WIDTH, PAGE_HEIGHT, removed_piece_ids, qr_code_b64)

    # --- 4. Save PDF and Return Bytes ---
    c.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    print(f"PDF bytes size before returning from generate_pdf: {len(pdf_bytes)}")
    return pdf_bytes


def main():
    """Main function to handle command-line arguments."""
    parser = argparse.ArgumentParser(description="Generate a SoChi BLOCKS puzzle PDF.")
    parser.add_argument("puzzle_path", help="Path to the puzzle JSON file.")
    parser.add_argument("master_pieces_path", help="Path to the master_pieces.json file.")
    parser.add_argument("--colors_path", default="backend/config/piece_colors.json", help="Path to the piece_colors.json file.")
    parser.add_argument("--removed_pieces", help="Comma-separated string of piece IDs to remove (e.g., 'V,W').")
    
    args = parser.parse_args()

    pdf_bytes = generate_pdf(args.puzzle_path, args.master_pieces_path, args.colors_path, args.removed_pieces)
    
    # In main, if run as a script, save the bytes to a file
    puzzle_id = os.path.basename(args.puzzle_path).split('.')[0] # Extract puzzle_id from path
    output_filename = os.path.join(OUTPUT_DIR, f"{puzzle_id}_problem.pdf")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(output_filename, 'wb') as f:
        f.write(pdf_bytes)
    print(f"PDF saved to {output_filename}")

if __name__ == "__main__":
    main()
