#!/usr/bin/env python3
"""
seed_db.py — コンテンツ公開に必要なマスターデータを DB へ投入する。

Docker コンテナを作り直した後、または新規環境セットアップ時に1度だけ実行する。
すでにレコードが存在する場合は何もしない (ON CONFLICT DO NOTHING)。

使い方:
  python scripts/seed_db.py

    (環境変数 DATABASE_URL が未設定の場合は localhost:5433 に接続する)
"""

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

# ── 設定 ──────────────────────────────────────────────────────────────

# PostgreSQL接続先
DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5433/sochi_blocks"
)

# ── マスターデータ定義 ────────────────────────────────────────────────

# content_puzzle.difficulty_id が参照するテーブル。
# テーブル名が不明な場合は psql で \dt を確認してください。
# 一般的な候補: master_difficulty / content_difficulty / puzzle_difficulty
DIFFICULTY_TABLE_CANDIDATES = [
    "master_difficulty",
    "content_difficulty",
    "puzzle_difficulty",
]

DIFFICULTIES = [
    {"id": "a1b2c3d4-0001-4000-8000-000000000001", "name": "Easy",    "order": 1},
    {"id": "a1b2c3d4-0002-4000-8000-000000000002", "name": "Medium",  "order": 2},
    {"id": "a1b2c3d4-0003-4000-8000-000000000003", "name": "Hard",    "order": 3},
    {"id": "a1b2c3d4-0004-4000-8000-000000000004", "name": "Hardest", "order": 4},
]


def detect_difficulty_table(conn) -> str | None:
    """存在するdifficultyテーブルを自動検出する。"""
    for tname in DIFFICULTY_TABLE_CANDIDATES:
        result = conn.execute(text(
            "SELECT to_regclass(:t)"
        ), {"t": tname}).scalar()
        if result is not None:
            return tname
    return None


def seed_difficulties(engine) -> None:
    with engine.connect() as conn:
        table = detect_difficulty_table(conn)
        if table is None:
            # content_puzzleのdifficulty_idが外部キーでない場合もあるので
            # テーブルが見つからなければスキップ
            print("  [SKIP] difficulty マスターテーブルが見つかりませんでした。")
            print("  候補: " + ", ".join(DIFFICULTY_TABLE_CANDIDATES))
            print("  content_puzzle.difficulty_id に外部キー制約がなければこのスキップは問題ありません。")
            return

        print(f"  [OK] difficulty テーブル検出: {table}")

        # カラム名を確認 (name か label かなど)
        cols = conn.execute(text(
            "SELECT column_name FROM information_schema.columns WHERE table_name = :t"
        ), {"t": table}).fetchall()
        col_names = {r[0] for r in cols}
        print(f"  カラム: {col_names}")

        name_col = "name" if "name" in col_names else ("label" if "label" in col_names else None)
        order_col = "sort_order" if "sort_order" in col_names else ("order" if "order" in col_names else None)

        for d in DIFFICULTIES:
            if name_col and order_col:
                sql = text(f"""
                    INSERT INTO {table} (id, {name_col}, {order_col})
                    VALUES (:id, :name, :order)
                    ON CONFLICT (id) DO NOTHING
                """)
                conn.execute(sql, {"id": d["id"], "name": d["name"], "order": d["order"]})
            elif name_col:
                sql = text(f"""
                    INSERT INTO {table} (id, {name_col})
                    VALUES (:id, :name)
                    ON CONFLICT (id) DO NOTHING
                """)
                conn.execute(sql, {"id": d["id"], "name": d["name"]})
            else:
                sql = text(f"""
                    INSERT INTO {table} (id)
                    VALUES (:id)
                    ON CONFLICT (id) DO NOTHING
                """)
                conn.execute(sql, {"id": d["id"]})

            print(f"  [OK] {d['name']:8s}  {d['id']}")

        conn.commit()
    print("  ✅ difficulty マスターデータ投入完了！")


def main():
    print(f"🔌 DB に接続中: {DB_URL}")
    engine = create_engine(DB_URL)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("  [OK] DB 接続成功")
    except Exception as e:
        print(f"  [ERROR] DB 接続失敗: {e}")
        sys.exit(1)

    print("\n📦 difficulty マスターデータを投入中...")
    seed_difficulties(engine)


if __name__ == "__main__":
    main()
