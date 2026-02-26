import subprocess
import os
import sys

def main():
    """
    データベースを起動し、0から14までのパズルファイルを生成します。
    """
    try:
        # データベースコンテナをバックグラウンドで起動する
        print("Starting database container...")
        subprocess.run(
            ["docker-compose", "-f", "infra/docker/docker-compose.yml", "up", "-d", "db"],
            check=True, capture_output=True
        )

        # 0から14までのインデックスでループ処理
        for i in range(15):
            puzzle_index = f"{i:04d}"
            puzzle_name = f"5x4x3_{puzzle_index}"
            output_file_path = os.path.join("gemini_work", "output", f"puzzle_{puzzle_name}.json")
            
            print(f"Generating puzzle for {puzzle_name}...")
            
            # 実行するコマンドを構築
            command = [
                "docker-compose",
                "-f", "infra/docker/docker-compose.yml",
                "run", "--rm",
                "backend",
                "poetry", "run", "python", "gemini_work/scripts/get_puzzle_json.py", puzzle_name
            ]
            
            # コマンドを実行し、標準出力をキャプチャ
            result = subprocess.run(
                command, capture_output=True, text=True, check=True, encoding='utf-8'
            )
            
            # 結果をファイルに書き込む
            with open(output_file_path, 'w', encoding='utf-8') as f:
                f.write(result.stdout)
        
        print("\nAll puzzle files have been generated successfully.")

    except subprocess.CalledProcessError as e:
        print("\nAn error occurred:", file=sys.stderr)
        print(f"Command: {' '.join(e.cmd)}", file=sys.stderr)
        print(f"Return code: {e.returncode}", file=sys.stderr)
        print(f"Output:\n{e.stdout}", file=sys.stderr)
        print(f"Error Output:\n{e.stderr}", file=sys.stderr)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
