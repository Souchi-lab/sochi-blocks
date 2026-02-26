import subprocess
import os
import sys
import json

# backendのモジュールをインポート可能にするため、プロジェクトルートをパスに追加
sys.path.append(os.getcwd())
from backend.scripts.generate_puzzle_pdf import generate_pdf, OUTPUT_DIR

def get_piece_ids(master_pieces_path):
    """master_pieces.jsonからピースIDのリストを取得します。"""
    with open(master_pieces_path, 'r', encoding='utf-8') as f:
        pieces = json.load(f)
    return [piece['id'] for piece in pieces]

def main():
    """
    0から14までのパズルJSONを元に、問題PDFを生成します。
    隠すピースの数は5ファイルごとに増やします。
    """
    master_pieces_path = os.path.join("gemini_work", "output", "master_pieces.json")
    colors_path = os.path.join("backend", "config", "piece_colors.json")

    try:
        all_piece_ids = get_piece_ids(master_pieces_path)
        print(f"Found piece IDs: {', '.join(all_piece_ids)}")

        # 出力ディレクトリを先に作成
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # 0から14までのインデックスでループ処理
        for i in range(15):
            if 0 <= i <= 4:
                num_to_remove = 3
            elif 5 <= i <= 9:
                num_to_remove = 4
            else:
                num_to_remove = 5

            if num_to_remove > len(all_piece_ids):
                print(f"Warning: Cannot remove {num_to_remove} pieces...", file=sys.stderr)
                removed_ids = all_piece_ids
            else:
                start_index = (i * num_to_remove) % len(all_piece_ids)
                rotated_ids = all_piece_ids[start_index:] + all_piece_ids[:start_index]
                removed_ids = rotated_ids[:num_to_remove]

            removed_pieces_str = ",".join(removed_ids)
            
            puzzle_index = f"{i:04d}"
            puzzle_name = f"puzzle_5x4x3_{puzzle_index}"
            puzzle_path = os.path.join("gemini_work", "output", f"{puzzle_name}.json")
            
            print(f"\nGenerating PDF for {puzzle_name} (removing {num_to_remove} pieces: {removed_pieces_str})...")
            
            # PDF生成関数を直接呼び出す
            pdf_bytes = generate_pdf(
                puzzle_path=puzzle_path,
                master_pieces_path=master_pieces_path,
                colors_path=colors_path,
                removed_pieces_str=removed_pieces_str
            )

            # 返されたバイトデータをファイルに保存
            output_filename = os.path.join(OUTPUT_DIR, f"{puzzle_name}_problem.pdf")
            with open(output_filename, 'wb') as f:
                f.write(pdf_bytes)
            print(f"Successfully saved {output_filename}")

        print(f"\nAll puzzle PDFs have been generated successfully in the '{OUTPUT_DIR}' directory.")

    except FileNotFoundError as e:
        print(f"\nError: A required file was not found: {e.filename}", file=sys.stderr)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
