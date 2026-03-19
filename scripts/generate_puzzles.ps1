# データベースコンテナをバックグラウンドで起動する
Write-Host "Starting database container..."
& "docker-compose" -f "infra/docker/docker-compose.yml" "up" "-d" "db"

# 0から14までのインデックスでループ処理
for ($i = 0; $i -le 14; $i++) {
    # ゼロパディングして4桁の文字列を作成 (例: 0000, 0001)
    $puzzleIndex = "{0:d4}" -f $i
    $puzzleName = "5x4x3_$puzzleIndex"
    $outputFile = "gemini_work/output/puzzle_$puzzleName.json"
    
    Write-Host "Generating puzzle for $puzzleName..."
    
    # & (呼び出し演算子) を使ってコマンドを安全に実行し、結果をファイルに保存
    & "docker-compose" -f "infra/docker/docker-compose.yml" "run" "--rm" "backend" "poetry" "run" "python" "gemini_work/scripts/get_puzzle_json.py" $puzzleName | Out-File -FilePath $outputFile -Encoding "utf8"
}

Write-Host "All puzzle files have been generated."
