# SoChi BLOCKS プロジェクト構造分析レポート

  1. 技術スタック概要


  | 領域 | 技術 | 詳細 |
  | :--- | :--- | :--- |
  | フロントエンド | React, TypeScript | UIフレームワークとしてReactを採用。静的型付けのためにTypeScriptを使用。 |
  | | Three.js | 3Dグラフィックス描画ライブラリ。@react-three/fiber を通じてReactと統合。 |
  | | Vite | 開発サーバーとビルドツール。高速な開発体験を提供。 |
  | | Vitest | Viteネイティブの単体テストフレームワーク。 |
  | バックエンド | Flask | Pythonの軽量なWebフレームワーク。 |
  | | PostgreSQL | リレーショナルデータベース。psycopg2-binary で接続。 |
  | | Alembic | データベーススキーマのマイグレーションツール。 |
  | インフラ | Docker, Docker Compose | コンテナ化技術。開発環境の構築とサービス（DB, Backend, Frontend）の管理。 |
  | 共通 | Poetry | Pythonの依存関係管理とパッケージングツール。 |

  2. ディレクトリ構造と責務



    1 C:.
    2 ├── .github/              # (未使用) GitHub Actions ワークフロー用
    3 ├── backend/              # Flaskバックエンド
    4 │   ├── config/           # 設定ファイル用
    5 │   ├── scripts/          # バックエンド関連のスクリプト
    6 │   └── utils/            # ユーティリティ関数
    7 ├── db/                   # データベース関連
    8 │   └── migrations/       # Alembicのマイグレーションスクリプト
    9 ├── docs/                 # (未使用) プロジェクトドキュメント用
   10 ├── frontend/             # Reactフロントエンド
   11 │   ├── public/           # 静的アセット (画像、フォントなど)
   12 │   ├── src/              # ソースコード
   13 │   │   ├── components/   # 再利用可能なReactコンポーネント
   14 │   │   │   ├── Viewer.tsx      # ★【重要】Three.jsの3Dビューア
   15 │   │   │   └── ...
   16 │   │   ├── hooks/        # カスタムフック (状態管理ロジック)
   17 │   │   │   └── useGameState.ts # ★【重要】ゲーム状態の管理
   18 │   │   ├── constants/    # 定数 (ピースの色など)
   19 │   │   ├── types/        # TypeScriptの型定義
   20 │   │   ├── utils/        # 汎用ユーティリティ関数
   21 │   │   ├── App.tsx       # ★【重要】アプリケーションのメインコンポーネント
   22 │   │   └── main.tsx      # ★【重要】Reactアプリケーションのエントリーポイント
   23 │   ├── package.json      # Node.jsの依存関係とスクリプト定義
   24 │   └── vite.config.ts    # Viteの設定ファイル
   25 ├── infra/                # インフラ構成
   26 │   └── docker/
   27 │       ├── docker-compose.yml  # ★【重要】開発環境の全サービスを定義
   28 │       ├── Dockerfile.backend  # Backendサービス用のDockerfile
   29 │       └── Dockerfile.frontend.dev # Frontendサービス用のDockerfile
   30 └── pyproject.toml        # ★【重要】PoetryによるPythonプロジェクト定義・依存関係


  3. 主要ファイルの責務


  infra/docker/docker-compose.yml
   - プロジェクト全体の司令塔。db, backend, frontend の3つのサービスを定義・連携させます。
   - db サービスは postgres:16 イメージから起動します。
   - backend サービスは Dockerfile.backend を使ってビルドされ、poetry run flask --app backend.app run コマンドで起動します。
   - frontend サービスは Dockerfile.frontend.dev を使い、Viteの開発サーバーを起動します。


  pyproject.toml
   - Python (バックエンド) の依存関係を定義します。
   - flask, psycopg2-binary, alembic などが含まれ、バックエンドの技術スタックを決定づけています。


  frontend/package.json
   - JavaScript (フロントエンド) の依存関係を定義します。
   - react, three, @react-three/fiber などが含まれ、フロントエンドが「React製のThree.jsアプリ」であることを示しています。

  frontend/src/main.tsx
   - フロントエンドの起動ファイル。
   - App コンポーネントをHTMLの root 要素にレンダリングします。


  frontend/src/App.tsx
   - アプリケーションのルートコンポーネント。
   - URLを解釈して動作モード（通常、キャプチャ等）を決定します。
   - useGameState フックを通じてゲームのすべての状態（ピースの配置、選択状態など）を管理します。
   - Viewer (3D表示部) や PieceTray (ピース選択部) などの主要UIコンポーネントを組み合わせて画面を構築する、アプリケーションの中心です。