# P1-06 GeminiCLI Runbook 🧑‍💻 (v0.3 / 2025-07-15)

> ## 変更ハイライト (v0.2 → v0.3)
>
> 1. \*\*.env と \*\*\`\` の必須化
> 2. **PostgreSQL データベース作成** を明示
> 3. `env.py` に **モデル全 import** を追加する手順を追記
> 4. Alembic の **リセット手順（**`** & **`**）** を追加
> 5. 成功チェックのコマンド例を更新

---

## 0. 前提

| 項目 バージョン / ポイント |                                        |
| --------------- | -------------------------------------- |
| ブランチ            | `feature/p1-06-dir-reorg` （dev から派生済み） |
| Python          | 3.12（Poetry）                           |
| DB              | PostgreSQL 16（ローカル / Unix ソケット推奨）      |

\`\`\*\* を必ず用意：\*\*

```
# .env
DATABASE_URL=postgresql:///sochi_blocks        # Unix-socket 接続
# TCP の場合:
# DATABASE_URL=postgresql://postgres:<password>@localhost:5432/sochi_blocks

```

---

## 1. ディレクトリ & ファイル整備

```
########## 1-1. backend 雛形 ##########
mkdir -p backend/{models,services,api}
echo -e "# placeholder\nprint('backend bootstrapped')" > backend/app.py

########## 1-2. schema.sql → db/ ##########
mkdir -p db
git mv schema.sql db/schema.sql

########## 1-3. Docker eco-system (最低限) ##########
mkdir -p infra/docker
cat > infra/docker/docker-compose.yml <<'YAML'
version: '3.9'
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: example
    ports:
      - "5432:5432"
YAML

########## 1-4. scripts / terraform プレースホルダ ##########
mkdir -p infra/{scripts,terraform}
echo -e "# Terraform IaC (placeholder)\n\n未実装です。TODO: Phase-3 で具体化。" > infra/terraform/README.md

########## 1-5. docs, tests 雛形 ##########
mkdir -p docs tests/unit

```

---

## 2. PostgreSQL 初期化

```
sudo -u postgres psql -c "CREATE DATABASE sochi_blocks;"   # 既にあればスキップ

```

*Unix ソケット接続* なら設定追加不要。
*TCP 接続* にしたい場合は `postgresql.conf` で `listen_addresses` を有効化し、`pg_hba.conf` に `host ... trust/md5` を追記する。

---

## 3. Alembic セットアップ

```
########## 3-1. Alembic インストール & 初期化 ##########
poetry add --group dev alembic
alembic init db/migrations

```

### 3-2. `alembic.ini` 編集

```
[alembic]
script_location = %(here)s/db/migrations
# sqlalchemy.url は env.py で .env から読み込む

```

### 3-3. `db/migrations/env.py` 主要追記

```
import os
from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool
from dotenv import load_dotenv

load_dotenv()
config = context.config
config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])

if config.config_file_name:
    fileConfig(config.config_file_name)

# --- 全モデル import ---
from backend.models.base import Base
from backend.models.master_user import MasterUser
from backend.models.master_difficulty import MasterDifficulty
from backend.models.master_puzzle_type import MasterPuzzleType
from backend.models.master_piece import MasterPiece
from backend.models.master_base_puzzle import MasterBasePuzzle
from backend.models.master_base_puzzle_cell import MasterBasePuzzleCell
from backend.models.content_puzzle import ContentPuzzle
from backend.models.content_puzzle_cell import ContentPuzzleCell

target_metadata = Base.metadata

```

---

## 4. Alembic リセット (エラー時の保険)

```
# 旧リビジョンが残ってエラーになる場合のみ
rm -rf db/migrations/versions/*
psql -d sochi_blocks -c 'DROP TABLE IF EXISTS alembic_version;'

```

---

## 5. マイグレーション実行

```
poetry run alembic revision --autogenerate -m "initial schema"
poetry run alembic upgrade head

```

成功確認：

```
psql -d sochi_blocks -c '\dt'                    # テーブル一覧
psql -d sochi_blocks -c 'SELECT * FROM alembic_version;'

```

---

## 6. テスト & CI

```
pytest -q || true                 # テスト未実装なら true で無視
poetry run alembic upgrade head   # no-op で終了することを確認

```

---

## 7. ドキュメント更新

* README の Getting Started に `.env` 手順を追記
* Roadmap 更新時は **必ず Project Lead に確認**！

---

## 8. コミット & PR フロー

```
git add .
git commit -m "feat: P1-06 dir reorg + Alembic bootstrap (v0.3)"
git push -u origin feature/p1-06-dir-reorg
gh pr create --title "feat: P1-06 dir reorg + Alembic bootstrap" \
             --body "Runbook v0.3 に基づきディレクトリ再編と Alembic 初期化を完了しました。"

```

**マージ条件**

1. CI Green
2. 2 Approvals
3. squash merge → `dev`

---

### MEMO

| 項目 ポイント  |                                                                      |
| -------- | -------------------------------------------------------------------- |
| 接続方式     | Unixソケット: `postgresql:///db` / TCP: `postgresql://user:pass@host/db` |
| Makefile | `make db-up` / `make migrate` など Phase-2 で追加予定                       |

> 🚀 **Gemini CLI**、この Runbook v0.3 を実行してね！
