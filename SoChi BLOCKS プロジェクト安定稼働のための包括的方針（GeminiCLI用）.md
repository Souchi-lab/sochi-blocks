<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" class="logo" width="120"/>

## SoChi BLOCKS プロジェクト安定稼働のための包括的方針（GeminiCLI用）

本プロジェクトで複数の課題が複合していたことを踏まえ、**サービスの安定化と構成の明確化**に重点を置いた運用指針を以下にまとめます。

### 1. 依存環境の構築とコンテナ設計

- **Poetry仮想環境をOFFで統一**
    - `POETRY_VIRTUALENVS_CREATE=false` の指定をDockerfileで行い、Pythonシステム環境に直接パッケージをインストールします。
    - `poetry install --no-root --only main,dev` を使い、必要なmain/dev依存を明示的に導入します。
- **マイグレーションファイルの適切な配置**
    - コンテナビルド時、`db/migrations/versions/` の全ファイルを必ずコンテナ内にコピーして置くことを徹底します。
- **docker-compose起動は必ずpoetry経由で行う**
    - 例：`command: poetry run python backend/app.py`
    - こうすることでPATHや仮想環境の実行混乱を失くします。


### 2. マイグレーション不整合・スキーマ管理方法

- **マイグレーションディレクトリの必ず全COPY**
    - Dockerfileで `COPY db/migrations/versions/ db/migrations/versions/` 等を忘れず指定。
    - 必要に応じて `alembic.ini` も確実にコンテナに配置。
- **Alembic Stamp・再構築運用**
    - マイグレーションの状態に不整合やエラー（例：DuplicateTable, NotNullViolation）が出た場合は：
        - `alembic stamp head` でDBとファイルを強制同期
        - あるいはDBボリューム削除→`docker compose up`で完全初期化
- **マイグレーション実行の適切な順番を徹底**
    - 必ず「DBスキーマをAlembicで最新化」→「データインポート」の順
    - スクリプトやFlask起動より前に完了させることでデータ不整合を防止


### 3. データ生成・インポート運用

- **Ruby/Pythonスクリプトはpoetry環境で統一実行**
    - 例：`poetry run python backend/solution_data_import.py`
    - これにより依存の乱れやPATH問題が発生しません。
- **データ投入は明示的コマンド実行で順序管理**
    - Alembicでスキーマ調整→データ生成→データ投入、と明確にワークフローを分けて問題発生時の切り分けを容易に。


### 4. Docker・Compose実用運用ノウハウ

- **ボリュームバインド運用時の注意**
    - Composeの`volumes`によるソースbind mountは、ビルド後イメージとの差異やPyPIキャッシュなどで不整合が出やすいです。開発では必ず`docker compose build --no-cache`後の`docker compose up`で起動を推奨。
- **エラー解析にはlogsで詳細把握**
    - 問題発生時は `docker logs sochi_backend` で詳細を取得し、どこでエラーが起きているのか早期特定


### 5. 開発/運用フロー・まとめ

1. `pyproject.toml`に依存（Flaskなど）を記載
2. `poetry lock` でロックファイル整備
3. Dockerイメージを `build --no-cache` で作成
4. `docker compose up` で各サービス起動
5. Alembicでマイグレーション（必要な場合は`stamp`含む）
6. データ生成インポートを順次実行
7. Flask（backend/app.py）サーバ稼動を確認
8. 問題時は `logs`・DB/マイグレーション履歴・volumes を点検し、上記を再実施

### 重要なポイント

- 仮想環境を"Poetry+システムPython"一元管理にすることで依存の食い違い・実行PATHの混乱をシャットアウト
- Alembicやマイグレーションファイルの「漏れ」と「重複」が最大の事故原因。ファイルコピー・履歴管理・up/stamp手順を厳守
- 必要な各作業の**"ステップごと正常動作を必ず確認"**しながら次に進めることが「積み重なった問題の摘出」に直結

不明点や追加で深堀りしたい課題があればご相談ください。この戦略で、複雑なエラー連鎖を一歩ずつクリアにできるはずです。

