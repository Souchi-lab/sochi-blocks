# CLAUDE.md — SoChi BLOCKS

> AI エージェント向けプロジェクトガイド。
> このファイルを読めば repo 全体を探索せずに開発を開始できる。

---

## 1. Project Overview

**SoChi BLOCKS** は、ペントミノ系の 3D パズルを通じて
空間認識・数学的思考・問題解決力を育てる教育向け Web アプリ。

- **本番 URL**: `https://souchi-lab.github.io/sochi-blocks`
- **ターゲット**: 子供〜大人（教室・家庭どちらでも使える）
- **コアループ**: SNS でパズルを見る → Web で 3D を操作して解く → 達成感を得る

---

## 2. Core Concept

```
パズル構造:
  3D グリッド（x, y, z）に 12 種のペントミノピースが配置される。
  "removed_pieces" に指定されたピースが問題（埋める対象）。
  プレイヤーは空きセルに正しい向きでピースを配置してクリアを目指す。

難易度:
  Easy    → 2 ピース除去
  Medium  → 4 ピース除去
  Hard    → 6 ピース除去
  Hardest → 8 ピース除去

ピース ID: F I L N P T U V W X Y Z（12種）
```

---

## 3. Tech Stack

### Frontend（`frontend/`）

| 技術 | バージョン | 役割 |
|------|-----------|------|
| React | 18 | UI フレームワーク |
| TypeScript | 5 | 型安全 |
| Vite | 5 | ビルド / 開発サーバ |
| Three.js | latest | 3D レンダリング |
| @react-three/fiber | latest | Three.js ↔ React ブリッジ |
| @react-three/drei | latest | OrbitControls 等のヘルパー |

### Backend / Scripts（`scripts/` `backend/`）

| 技術 | 役割 |
|------|------|
| Python 3.11 + Poetry | スクリプト実行環境 |
| Flask | API サーバ（軽量） |
| PostgreSQL 16 | パズル DB |
| SQLAlchemy | ORM |
| Playwright | ブラウザ自動化（動画生成・TikTok 投稿） |
| Pillow | 2D 画像生成（layer.png） |
| ffmpeg | 動画トリミング |

### Deployment

| 場所 | 内容 |
|------|------|
| `docs/` | GitHub Pages ソース（公開アセット置き場） |
| Flask API | バックエンド（ローカル or サーバ） |

---

## 4. Repository Structure

```
SoChi BLOCKS/
│
├── frontend/                      ★ Web アプリ本体
│   ├── src/
│   │   ├── App.tsx                ★ ルートコンポーネント / URL パラメータ解析 / ゲーム統合
│   │   ├── hooks/
│   │   │   ├── useGameState.ts    ★ ゲーム状態管理（useReducer）
│   │   │   └── useAutoPlayer.ts     自動再生（SNS 動画生成用）
│   │   ├── components/
│   │   │   ├── Viewer.tsx         ★ Three.js Canvas（3D シーン）
│   │   │   ├── PuzzleVoxels.tsx   ★ 3D ボクセル描画
│   │   │   ├── PieceTray.tsx        ピース選択トレイ
│   │   │   ├── RotationCandidates.tsx  24方向回転サムネイル
│   │   │   ├── RotationControls.tsx   回転操作UI
│   │   │   ├── VictoryOverlay.tsx     クリア画面
│   │   │   ├── TutorialOverlay.tsx    チュートリアル
│   │   │   ├── SNSOverlay.tsx         SNS 動画用オーバーレイ
│   │   │   └── ShareResult.tsx        シェア画面
│   │   ├── utils/
│   │   │   ├── rotations.ts       ★ 24方向回転行列（Vec3, Mat3）
│   │   │   └── placement.ts       ★ 配置バリデーション（validAnchors, placementCells）
│   │   ├── types/
│   │   │   └── puzzle.ts            PuzzleData / PuzzleCell / PuzzleGrid 型定義
│   │   └── constants/
│   │       ├── pieceColors.ts       ピース色・形状マスタ
│   │       └── siteConfig.ts        SITE_URL / SITE_NAME
│   └── public/
│       ├── puzzles/               ★ puzzle_YYYYMMDD_NNN.json（パズルデータ）
│       ├── colors/
│       │   ├── piece_colors.json    ピース色定義
│       │   └── master_pieces.json   ピース形状定義
│       └── sns_videos/              SNS 動画生成一時置き場
│
├── scripts/                       ★ 自動化スクリプト
│   ├── auto_publish.py            ★ 全工程の司令塔（パズル生成→画像→動画→SNS投稿）
│   ├── generate_instagram_images.py  layer.png + 3D キャプチャ + キャプション生成
│   ├── publish_tiktok_browser.py     [TikTok] Playwright 投稿
│   ├── publish_instagram_reel.py     [Instagram Reel] Meta API 投稿
│   ├── publish_instagram_carousel.py [Instagram Carousel] Meta API 投稿
│   └── publish_instagram.py          Meta API 共通関数（後方互換）
│
├── docs/                          ★ GitHub Pages 公開領域（外部公開 = 全公開）
│   ├── index.html                   Web アプリ
│   ├── viewer.html                  3D ビューワ
│   ├── images/YYYYMMDD/NNN/         layer.png, 3d_x.png, 3d_y.png, caption_*.txt
│   ├── sns_videos/                  _full.mp4, _tiktok.mp4, _instagram.mp4
│   ├── puzzles/                     puzzle_*.json + manifest.json
│   └── share/                       OG タグ付きシェアページ
│
├── runbooks/                      内部ドキュメント（公開されない）
│   └── SNS_PUBLISH_RUNBOOK.md
│
├── backend/                       Flask API
│   └── scripts/generate_puzzle_video.py
│
├── db/migrations/                 Alembic マイグレーション
├── infra/docker/                  docker-compose.yml
├── CLAUDE.md                      ← このファイル
└── .env                           ★ 秘匿情報（Git 管理外）
```

---

## 5. Puzzle System

### データフォーマット（`puzzle_YYYYMMDD_NNN.json`）

```json
{
  "puzzle_id": "20260312_004",
  "grid": { "x": 4, "y": 4, "z": 3 },
  "cells": [
    { "x": 0, "y": 0, "z": 0, "piece": "F" },
    ...
  ],
  "removed_pieces": ["F", "I", "L", "N"]
}
```

### パズル ID の命名規則

```
YYYYMMDD_NNN
  └─ 20260312_004 = 2026年3月12日の4問目
```

### ファイルの二重管理

同一パズルが 2 箇所に存在する：
- `frontend/public/puzzles/puzzle_XXX.json` — Vite dev server が参照（開発用）
- `docs/puzzles/puzzle_XXX.json` — GitHub Pages が参照（本番用）

**自動生成時は両方に書き込む（`auto_publish.py` が管理）。**

### DB テーブル（PostgreSQL）

| テーブル | 役割 |
|---------|------|
| `master_base_puzzle` | ベースパズルのメタ情報 |
| `master_base_puzzle_cell` | セル座標とピース割り当て |
| `content_puzzle` | 公開済みパズル（code, difficulty, removed_pieces） |

---

## 6. Gameplay Design

### 状態管理（`useGameState.ts`）

```typescript
GameState {
  phase: 'idle' | 'playing' | 'victory'
  removedPieces: string[]      // 問題（埋めるべきピース）
  placedPieces: Set<string>    // 配置済みピース
  placedCells: Map<coordKey, pieceId>  // "x,y,z" → pieceId
  selectedPiece: string | null
  rotationIndex: number        // 0-23（24方向）
  cursorIndex: number          // 有効配置位置のインデックス
  mistakeCount: number
}
```

`useReducer` パターンで管理。副作用は `useEffect` に分離済み。

### 回転システム（`rotations.ts`）

- 3D 整数格子上の **24通りの固有回転行列** をアルゴリズムで生成
- 手書き禁止（アルゴリズム生成のみ）
- `Vec3 = [number, number, number]`
- `Mat3 = [[...], [...], [...]]`

### 配置バリデーション（`placement.ts`）

```typescript
validAnchors(data, placedCells, piece, rotIdx, removedPieces): Vec3[]
placementCells(data, anchor, piece, rotIdx): string[]
```

- `validAnchors` → 現在の回転で配置可能なアンカー座標一覧
- `placementCells` → アンカー+回転からセル座標文字列配列を返す

### URL パラメータ

```
?puzzle_id=20260312_004          パズルID
&removed_pieces=F,I,L,N          除去ピース（上書き）
&mode=capture&angle=x            スクリーンショット用
&autoplay=1&delay=500            自動再生（動画生成用）
&sns=1&video_mode=full_play      SNS動画オーバーレイ
```

---

## 7. UI Philosophy

- **シンプル・直感的**: フレームワーク固有のパターンを最小化。コンポーネントは小さく保つ
- **3D 空間の見せ方**: OrbitControls でドラッグ回転。y 軸上方向を固定
- **視覚的フィードバック**: ゴーストセル（配置プレビュー）、エラーフラッシュ、回転候補サムネイル
- **モバイル互換**: タッチ操作・スマホ画面幅を考慮した CSS
- **教育的配慮**: 派手なエフェクトより「考える時間」を尊重した落ち着いたデザイン

### 3D シーン構成

```
Canvas (fov=40, bg=#f5f5f5)
  ├── ambientLight (intensity=1.5)
  ├── directionalLight (position=[5,8,5], intensity=2.0)
  ├── OrbitControls
  ├── PuzzleVoxels (既存ピース・除去セル・ゴースト)
  └── AxisArrows
```

---

## 8. Coding Rules

### 絶対ルール

```
✅ React + TypeScript は既存の確立された基盤として維持する
✅ 小さな関数に分割（1関数 = 1責務）
✅ 型安全を保つ（any は原則禁止）
✅ モバイル互換を維持する
✅ 既存のコーディングスタイルに揃える

❌ React / TypeScript の上に新たなフレームワークを乗せない
❌ 状態管理ライブラリを導入しない（Redux, Zustand など）
❌ 不要な依存パッケージを追加しない
❌ コンポーネントを巨大化させない
❌ セキュリティホール（XSS, インジェクション）を作らない
```

### Python スクリプトのルール

```
✅ Poetry で依存を管理する
✅ エラーは [SNS種別] プレフィックス付きでログ出力する
✅ 既存関数（publish_instagram.py）を再利用する
✅ 失敗してもプロセス全体を止めない（WARN で続行）

❌ .env の内容をログに出力しない
❌ tiktok_cookies.json をコードにハードコードしない
```

### ファイル命名

```
コンポーネント:  PascalCase.tsx
フック:          useXxx.ts
ユーティリティ:  camelCase.ts
パズルファイル:  puzzle_YYYYMMDD_NNN.json
動画ファイル:    YYYYMMDD_NNN_{tiktok|instagram|full}.mp4
```

---

## 9. Development Strategy

### 変更前に必ず確認する

```
1. 影響範囲を特定する
   - フロントエンドのみ？ スクリプトのみ？ 両方？
2. 既存テストを確認する
   frontend/src/utils/__tests__/
   frontend/src/hooks/__tests__/
3. 設計を提案してからコードを書く
```

### 重要な依存関係

```
App.tsx
  └─ useGameState.ts（ゲーム状態）
  └─ Viewer.tsx → PuzzleVoxels.tsx（3D描画）
  └─ utils/rotations.ts（回転計算）
  └─ utils/placement.ts（配置バリデーション）

auto_publish.py
  └─ generate_instagram_images.py（画像・キャプション生成）
  └─ publish_instagram_reel.py / publish_instagram_carousel.py（SNS投稿）
```

### 変更してはいけない箇所

| ファイル / 関数 | 理由 |
|----------------|------|
| `rotations.ts` の行列生成アルゴリズム | 数学的正確性が必要。変更は全テストが通過した場合のみ |
| `PuzzleData` 型 | JSON フォーマットに直結。変更時はデータ移行が必要 |
| `docs/` 内のパズル JSON | 本番データ。git push で即公開される |
| `.env` / `tiktok_cookies.json` | 秘匿情報。コードに書かない、ログに出さない |

---

## 10. AI Development Workflow

### このプロジェクトにおける Claude Code の役割

```
ChatGPT    → 設計 / アーキテクチャ検討
Claude Code → 実装 / 修正 / デバッグ / レビュー
```

### Claude Code が作業を開始するときのチェックリスト

```
□ このファイル（CLAUDE.md）を読んだか
□ 変更対象のファイルを Read ツールで読んだか
□ 既存パターンを理解してから書き始めているか
□ 設計を説明してからコードを書いているか（いきなり実装しない）
```

### よくある作業パターン

**フロントエンドの UI 変更**
```
1. 対象コンポーネントを Read
2. useGameState.ts の関係するアクションを確認
3. 変更案を提示 → 承認後に Edit
```

**新しいパズル機能の追加**
```
1. puzzle.ts の型定義を確認
2. rotations.ts / placement.ts への影響を確認
3. テストファイルを確認
4. 実装 → テスト実行
```

**SNS 投稿スクリプトの修正**
```
1. auto_publish.py → publish_*.py の呼び出し関係を確認
2. 既存のエラーハンドリングパターンに揃える
3. [SNS種別] プレフィックスをログに付ける
```

### よく参照するファイル（ショートカット）

| 目的 | 参照先 |
|------|--------|
| 型定義を確認 | `frontend/src/types/puzzle.ts` |
| ゲーム状態の Action を追加 | `frontend/src/hooks/useGameState.ts` |
| 新しいコンポーネントを作る | `frontend/src/components/PieceTray.tsx`（既存例） |
| パズルデータの確認 | `docs/puzzles/puzzle_20260312_004.json` |
| SNS 投稿フローを確認 | `runbooks/SNS_PUBLISH_RUNBOOK.md` |
| DB 接続 | `scripts/auto_publish.py` の `get_engine()` |

### 環境変数（`.env`）

```env
# Instagram API
INSTAGRAM_BUSINESS_ACCOUNT_ID=...
FACEBOOK_PAGE_ACCESS_TOKEN=...

# PostgreSQL
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/sochi_blocks
```

### ローカル開発の起動

```bash
# フロントエンド
npm run dev --prefix frontend    # → http://localhost:5173

# DB（Docker）
docker compose -f infra/docker/docker-compose.yml up db

# Python 環境
poetry install
```
