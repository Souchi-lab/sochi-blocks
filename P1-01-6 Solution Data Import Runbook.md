---
title: "P1-01-6 Solution Data Import Runbook"
owner: "SoChi‑lab Backend Team"
version: "0.5.0"
last_updated: "2025-07-17"
status: "active"
tags: [runbook, data‑import, core‑foundation]
---

# 🎯 Purpose

Pentomino／SoChi Blocks 向け **60セル解データ** を `master_base_puzzle` / `master_base_puzzle_cell` にバルク投入するための **ワンショット手順** を定義する。Ruby 製 Solver で得た解データを **UUID + code** で保存し、既存 UUID スキーマとの整合を維持する。

---

## 🗺️ Overview

```mermaid
flowchart LR
    A[Ruby solver] -- JSON --> B[Importer (Python)] -- INSERT --> C[(PostgreSQL)]
    C --> D[master_base_puzzle]
    C --> E[master_base_puzzle_cell]
```

1.  **Ruby solver** が解データを含むJSONファイルを出力 (`solutions_5x4x3.json` 等)
2.  **Importer** (`solution_data_import.py`) がそれを読み取り、DBに一括登録
3.  この全工程は、必要に応じて手動で実行される。

---

## 📐 Schema Alignment

| テーブル | カラム | 型 | 説明 |
| :--- | :--- | :--- | :--- |
| `master_base_puzzle` | `id` | **UUID** (PK) | 決定論的 UUID → `uuid.uuid5(uuid.NAMESPACE_DNS, code)` |
| 〃 | `name` | **String(16)**, `unique`, `NOT NULL` | 人間可読スラッグ `5x4x3_0000` |
| `master_base_puzzle_cell` | `base_puzzle_id` (FK) | UUID | 上記 `id` を参照 |
| 〃 | `value` (FK) | String(1) | どのピース ('F', 'I', 'L'など) かを示す |

> **Why not String PK?** 既存テーブルの UUID 一貫性を保ちつつ、REST/API で扱い易い `code` を併設。

---

## 🔧 Prerequisites

*   **Alembic migration** で `name` カラムおよび `value` カラムが追加済みであること。（⇒ § Migration）
*   **Docker**: `infra/docker/Dockerfile.backend` に Ruby がインストールされていること。

    ```dockerfile
    # Use apt-get for Debian-based images
    RUN apt-get update && apt-get install -y ruby ruby-json
    COPY tools/pentomino/ /opt/solver/
    ```

---

## 0️⃣ Migration – add `name` and `value`

`name` カラムと `value` カラムは、初期マイグレーションで追加済み。手動で追加する場合、以下のコマンドを実行し、モデルとの差分を検出してマイグレーションスクリプトを生成する。

```bash
# (Run from project root)
docker compose exec backend poetry run alembic -c /workspace/alembic.ini revision --autogenerate -m "Update master_base_puzzle_cell for value"
```

生成されたスクリプトに `op.add_column` が含まれていることを確認し、`poetry run alembic -c /workspace/alembic.ini upgrade head` で適用する。

---

## 1️⃣ Ruby solver: `--json-out`

*   **File**: `tools/pentomino/solver.rb`
*   **Function**: このスクリプトはペントミノパズルの解を探索し、`--json-out` で指定されたファイルにJSON形式で出力する。1つのJSONファイルには複数の解が含まれ、各解は12個のピース（F, I, L, P, N, T, U, V, W, X, Y, Z）とそれぞれのセル座標のリストで構成される。
*   **Actual Code**: 

    ```bash
    # (Run from infra/docker directory)
    docker compose exec backend poetry run ruby tools/pentomino/solver.rb --size 5x4x3 --json-out /workspace/infra/docker/solutions_5x4x3.json
    ```
    **Example JSON Output (truncated for brevity):**
    ```json
    [
      [
        {
          "piece": "F",
          "cells": [
            [4, 2, 0], [4, 0, 1], [4, 1, 1], [4, 2, 1], [4, 1, 2]
          ]
        },
        {
          "piece": "I",
          "cells": [
            [0, 0, 0], [1, 0, 0], [2, 0, 0], [3, 0, 0], [4, 0, 0]
          ]
        },
        // ... 12個のピースが続く
      ],
      // ... 他の解答が続く
    ]
    ```

---

## 2️⃣ Python importer (`backend/scripts/solution_data_import.py`)

このスクリプトは、JSONファイルを読み込み、データベースにパズルとセルのデータをインポートする。

*   **Foreign Keys**: `get_or_create` 関数が `MasterPiece`, `MasterBasePuzzle`, `MasterUser` などの依存先ダミーデータを先に生成する。
*   **Data Structure**: 1つのJSONファイルは複数のパズル解（ピースのリスト）に対応している。スクリプトはこの構造を解釈し、`MasterBasePuzzle` と `MasterBasePuzzleCell` のレコードを作成する。
*   **Bulk Insert**: `session.bulk_save_objects` を使用してセルデータを効率的に挿入する。

---

## 3️⃣ Execution via Docker Compose

データインポートは、以下のコマンドで手動で実行する。

*   **Command**:

    ```bash
    # (Run from infra/docker directory)
    docker compose exec backend poetry run python backend/scripts/solution_data_import.py --json-dir /workspace/infra/docker --size 5x4x3
    ```

---

## 🧪 Verification

| 手順 | コマンド | 期待結果 |
| :--- | :--- | :--- |
| 1. コンテナ起動 | `docker-compose up -d --build backend` | エラーなく起動 |
| 2. ログ確認 | `docker-compose logs -f backend` | `INFO Imported 3940 puzzles (...)` が表示される |
| 3. DB確認 | `docker-compose exec db psql -U postgres -d sochi_blocks -c "SELECT count(*) FROM master_base_puzzle;"` | `count` が `3940` である |
| 4. 個別解の確認 | `docker-compose exec db psql -U postgres -d sochi_blocks -c "SELECT p.name AS puzzle_name, c.value AS piece_id, c.x, c.y, c.z FROM master_base_puzzle AS p JOIN master_base_puzzle_cell AS c ON p.id = c.base_puzzle_id WHERE p.name = '5x4x3_0000' ORDER BY c.value, c.z, c.y, c.x;"` | 60行のデータが、12種類のpiece_idと共に表示される |

---

## 🚦 Done Criteria

1.  `master_base_puzzle` に `name` が存在し `unique index` が付いている。
2.  `master_base_puzzle_cell` に `value` が存在し、正しくデータが格納されている。
3.  データインポート手順が明確に定義され、手動で実行できる。
4.  Roadmap: `P1‑01‑6 Solution_Data_Import` → **Done**