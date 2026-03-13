# SoChi BLOCKS — SNS 投稿システム 運用手順書

> 最終更新: 2026-03-13
> 対象読者: 日次運用担当者

---

## 目次

1. [SNS 戦略の概要](#1-sns-戦略の概要)
2. [前提条件・初期セットアップ](#2-前提条件初期セットアップ)
3. [日次運用フロー（全自動）](#3-日次運用フロー全自動)
4. [SNS 別の投稿手順](#4-sns-別の投稿手順)
   - 4-1. TikTok
   - 4-2. Instagram Reel
   - 4-3. Instagram Carousel
5. [素材ファイルの確認方法](#5-素材ファイルの確認方法)
6. [手動で特定パズルを再投稿する](#6-手動で特定パズルを再投稿する)
7. [エラー対処一覧](#7-エラー対処一覧)
8. [ファイル構成リファレンス](#8-ファイル構成リファレンス)
9. [スクリプト引数リファレンス](#9-スクリプト引数リファレンス)

---

## 1. SNS 戦略の概要

SoChi BLOCKS のSNS 配信は **「発見 → カタログ → 体験」** の三層で設計されている。

```
TikTok       → 発見（新規ユーザー）
    ↓
Instagram    → カタログ（パズル図鑑）
    ↓
Web アプリ   → 体験（実際に遊ぶ）
```

| SNS | 役割 | 動画 | 解答 | カバー画像 |
|-----|------|------|------|-----------|
| **TikTok** | 発見・拡散 | `_tiktok.mp4`（0-8s） | **なし** | 任意 |
| **Instagram Reel** | ブランド露出 | `_instagram.mp4`（0-12s） | **あり** | 任意 |
| **Instagram Carousel** | パズルカタログ | 動画 + 画像 | **あり** | **`layer.png` 必須** |

### layer.png について（重要）

```
layer.png = パズルカタログ表紙
```

Instagram プロフィールのグリッドに `layer.png` が並ぶことで、
プロフィール全体が **パズル図鑑** のように見える。
Instagram Carousel 投稿において `layer.png` は **必須** であり、
存在しない場合は投稿スクリプトがエラーで停止する。

---

## 2. 前提条件・初期セットアップ

### 2-1. 必要なツール

| ツール | 用途 | 確認コマンド |
|--------|------|-------------|
| Python 3.11+ | スクリプト実行 | `python --version` |
| Poetry | Python 依存管理 | `poetry --version` |
| Node.js 18+ | フロントエンド / 動画生成 | `node --version` |
| ffmpeg | 動画トリミング | `ffmpeg -version` |
| PostgreSQL | パズルDB | `psql --version` |

### 2-2. 環境変数（`.env`）

プロジェクトルートの `.env` に以下を設定する：

```env
# Instagram（Carousel / Reel）
INSTAGRAM_BUSINESS_ACCOUNT_ID=your_ig_account_id
FACEBOOK_PAGE_ACCESS_TOKEN=your_page_access_token

# PostgreSQL
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/sochi_blocks
```

### 2-3. TikTok クッキーの準備

TikTok 投稿は Playwright（ブラウザ自動化）で行うため、
ログイン済みクッキーが必要。

```
scripts/tiktok_cookies.json
```

**作成手順：**
1. Chrome で https://www.tiktok.com を開き、ログインする
2. Chrome 拡張「EditThisCookie」または「Cookie-Editor」をインストール
3. TikTok ページでクッキーを JSON エクスポート
4. `scripts/tiktok_cookies.json` として保存

> クッキーの有効期限が切れた場合は同手順で更新する。

### 2-4. 依存パッケージのインストール

```bash
# Python 依存
poetry install

# Playwright ブラウザのインストール（初回のみ）
poetry run playwright install chromium

# フロントエンド依存
npm install --prefix frontend
```

---

## 3. 日次運用フロー（全自動）

### 推奨コマンド（毎日 1 回実行）

```bash
poetry run python scripts/auto_publish.py \
  --all \
  --instagram-carousel \
  --instagram-reel \
  --tiktok
```

このコマンドで以下がすべて実行される：

```
[1] 難易度 Easy / Medium / Hard / Hardest を 1 問ずつ選出
[2] パズル JSON を DB からエクスポート → frontend/public/puzzles/
[3] layer.png（2D レイヤー画像）を生成
[4] 3D キャプチャ（x 方向 / y 方向）を生成
[5] SNS 動画を生成
    └─ _full.mp4（0-12s）
    └─ _tiktok.mp4（0-8s trim）← ffmpeg
    └─ _instagram.mp4（full コピー）
[6] キャプションを生成
    └─ caption_tiktok.txt
    └─ caption_instagram.txt
    └─ caption_twitter.txt
[7] DB に保存
[8] GitHub Pages へ push
[9] Instagram Carousel 投稿（layer.png をカバーに）
[10] Instagram Reel 投稿
[11] TikTok 投稿（ブラウザ起動 → 半自動）
```

### TikTok の半自動ステップについて

TikTok 投稿時はブラウザが起動し、以下のメッセージが表示される：

```
============================================================
  Ready to post!

  The browser is open. Please:
    1. Review the video preview and caption.
    2. Adjust privacy / settings if needed.
    3. Click the [Post] button to publish.

  Press Enter here when you are done (or to cancel).
============================================================
```

内容を確認して投稿ボタンを押し、完了後に Enter キーを押す。

---

## 4. SNS 別の投稿手順

### 4-1. TikTok

**役割：** 発見・新規ユーザー獲得
**動画：** `_tiktok.mp4`（0-8s、解答なし）
**キャプション：** `caption_tiktok.txt`

```bash
# パズル生成 + TikTok 投稿のみ
poetry run python scripts/auto_publish.py --difficulty hard --tiktok

# 特定の既存素材から TikTok だけ投稿
poetry run python scripts/publish_tiktok_browser.py \
  --video docs/sns_videos/20260312_004_tiktok.mp4 \
  --caption docs/images/20260312/004/caption_tiktok.txt
```

**TikTok のルール：**
- 動画は 0-8s（解答を含まない）
- 動画は必ず動きから始まる（静止盤面スタート禁止）
- キャプションは短文・フック重視

---

### 4-2. Instagram Reel

**役割：** ブランド露出・フォロワー継続配信
**動画：** `_instagram.mp4`（0-12s、解答あり）
**キャプション：** `caption_instagram.txt`

```bash
# パズル生成 + Instagram Reel 投稿のみ
poetry run python scripts/auto_publish.py --difficulty hard --instagram-reel

# 特定の既存素材から Instagram Reel だけ投稿
poetry run python scripts/publish_instagram_reel.py \
  --puzzle-id 20260312_004 \
  --dir docs/images/20260312/004/ \
  --base-url https://souchi-lab.github.io/sochi-blocks
```

**Instagram Reel のルール：**
- 動画は 0-12s（解答あり）
- 保存・シェアを促すキャプション

---

### 4-3. Instagram Carousel

**役割：** パズルカタログ（プロフィールを図鑑化）
**カバー画像：** `layer.png`（**必須**）
**キャプション：** `caption_instagram.txt`

```bash
# パズル生成 + Instagram Carousel 投稿のみ
poetry run python scripts/auto_publish.py --difficulty hard --instagram-carousel

# 特定の既存素材から Instagram Carousel だけ投稿
poetry run python scripts/publish_instagram_carousel.py \
  --dir docs/images/20260312/004/ \
  --base-url https://souchi-lab.github.io/sochi-blocks
```

**Instagram Carousel のルール：**
- `layer.png` がなければ投稿不可（エラーで停止）
- カバーは必ず `layer.png`（パズル図鑑のカタログ表紙）
- コンテンツ順：`layer.png` → `3d_x.png` → `3d_y.png`（動画あれば先頭）

---

## 5. 素材ファイルの確認方法

投稿前に素材が正しく生成されているか確認する。

```
docs/images/YYYYMMDD/NNN/
  ├── layer.png              ✅ Carousel カバー（必須）
  ├── 3d_x.png               ✅ 3D アングル X
  ├── 3d_y.png               ✅ 3D アングル Y
  ├── caption_tiktok.txt     ✅ TikTok 用キャプション
  ├── caption_instagram.txt  ✅ Instagram 用キャプション
  ├── caption_twitter.txt    ✅ Twitter 用キャプション
  └── url.txt                ✅ ビューワー URL

docs/sns_videos/
  ├── YYYYMMDD_NNN_full.mp4       ✅ 元動画（0-12s）
  ├── YYYYMMDD_NNN_tiktok.mp4     ✅ TikTok 用（0-8s）
  └── YYYYMMDD_NNN_instagram.mp4  ✅ Instagram 用（full コピー）
```

### キャプション確認コマンド

```bash
# TikTok キャプション
cat docs/images/20260312/004/caption_tiktok.txt

# Instagram キャプション
cat docs/images/20260312/004/caption_instagram.txt
```

---

## 6. 手動で特定パズルを再投稿する

すでに生成済みの素材を使って特定のパズルだけ投稿し直す場合。

### --dir オプションを使う（生成をスキップ）

```bash
# 既存素材ディレクトリを指定して Instagram Carousel だけ投稿
poetry run python scripts/auto_publish.py \
  --dir docs/images/20260312/004 \
  --instagram-carousel

# Instagram Reel だけ投稿
poetry run python scripts/auto_publish.py \
  --dir docs/images/20260312/004 \
  --instagram-reel
```

### 個別スクリプトを直接呼ぶ

```bash
# TikTok
poetry run python scripts/publish_tiktok_browser.py \
  --video docs/sns_videos/20260312_004_tiktok.mp4 \
  --caption docs/images/20260312/004/caption_tiktok.txt

# Instagram Reel
poetry run python scripts/publish_instagram_reel.py \
  --puzzle-id 20260312_004 \
  --dir docs/images/20260312/004 \
  --base-url https://souchi-lab.github.io/sochi-blocks

# Instagram Carousel
poetry run python scripts/publish_instagram_carousel.py \
  --dir docs/images/20260312/004 \
  --base-url https://souchi-lab.github.io/sochi-blocks
```

---

## 7. エラー対処一覧

### `[Instagram Carousel] ERROR: Instagram carousel requires layer.png`

**原因：** `layer.png` が存在しない
**対処：**
```bash
# layer.png を単体生成
poetry run python scripts/generate_instagram_images.py \
  --puzzle_id 20260312_004
```
生成後に Carousel 投稿を再実行する。

---

### `[TikTok] ERROR: No video found for YYYYMMDD_NNN`

**原因：** `_tiktok.mp4` も `_full.mp4` も存在しない
**対処：**
```bash
# SNS 動画を再生成（frontend が必要）
cd frontend
npm run generate-sns -- 20260312_004 full_play
```
または ffmpeg で手動トリム：
```bash
ffmpeg -i docs/sns_videos/20260312_004_full.mp4 \
  -t 8 -c copy docs/sns_videos/20260312_004_tiktok.mp4
```

---

### `[Instagram Reel] ERROR: No caption file found`

**原因：** `caption_instagram.txt` / `caption.txt` が両方存在しない
**対処：**
```bash
# キャプションを再生成
poetry run python scripts/generate_instagram_images.py \
  --puzzle_id 20260312_004
```

---

### `Error: TikTok session is invalid or expired.`

**原因：** TikTok クッキーの有効期限切れ
**対処：**
1. Chrome で TikTok にログイン
2. EditThisCookie でクッキーをエクスポート
3. `scripts/tiktok_cookies.json` を上書き保存
4. 再実行

---

### `Error: Missing Instagram credentials in .env`

**原因：** `.env` に `INSTAGRAM_BUSINESS_ACCOUNT_ID` / `FACEBOOK_PAGE_ACCESS_TOKEN` が未設定
**対処：** `.env` を確認・修正してから再実行する。

---

### GitHub Pages に画像が表示されない（Instagram API エラー）

**原因：** push 直後は GitHub Pages がまだ反映されていない
**対処：** auto_publish.py は push 後に GitHub Pages の疎通チェックを自動で行い、
最大 5 分間リトライする。それ以上かかる場合は数分待って手動で Carousel/Reel を投稿する。

---

## 8. ファイル構成リファレンス

```
SoChi BLOCKS/
│
├── scripts/
│   ├── auto_publish.py                ← 全工程の司令塔
│   ├── generate_instagram_images.py   ← layer.png / 3D画像 / キャプション生成
│   ├── publish_tiktok_browser.py      ← [TikTok] Playwright 投稿
│   ├── publish_instagram_reel.py      ← [Instagram Reel] Meta API 投稿
│   ├── publish_instagram_carousel.py  ← [Instagram Carousel] Meta API 投稿（layer.png 必須）
│   ├── publish_instagram.py           ← Meta API 共通関数（後方互換）
│   └── tiktok_cookies.json            ← TikTok ログイン済みクッキー（Git 管理外）
│
├── docs/
│   ├── images/
│   │   └── YYYYMMDD/
│   │       └── NNN/
│   │           ├── layer.png              ← Carousel 表紙（必須）
│   │           ├── 3d_x.png
│   │           ├── 3d_y.png
│   │           ├── caption_tiktok.txt
│   │           ├── caption_instagram.txt
│   │           ├── caption_twitter.txt
│   │           └── url.txt
│   ├── sns_videos/
│   │   ├── YYYYMMDD_NNN_full.mp4       ← 元動画（0-12s）
│   │   ├── YYYYMMDD_NNN_tiktok.mp4     ← TikTok 用（0-8s）
│   │   └── YYYYMMDD_NNN_instagram.mp4  ← Instagram 用（full コピー）
│   ├── puzzles/
│   │   └── puzzle_YYYYMMDD_NNN.json
│   └── share/
│       └── YYYYMMDD_NNN.html           ← OG タグ付きシェアページ
│
└── frontend/public/
    ├── puzzles/                        ← フロントエンド向け puzzle JSON
    └── sns_videos/                     ← 動画生成一時置き場
```

---

## 9. スクリプト引数リファレンス

### auto_publish.py

```
python scripts/auto_publish.py [オプション]

生成オプション（どれか 1 つ必須）:
  --difficulty [easy|medium|hard|hardest]  指定難易度 1 問を生成
  --all                                    全難易度（easy/medium/hard/hardest）を生成
  --dir PATH                               既存素材ディレクトリを指定（生成スキップ）

投稿オプション（複数指定可）:
  --tiktok                [TikTok] Playwright でブラウザ投稿
  --instagram-reel        [Instagram Reel] Meta API で Reel 投稿
  --instagram-carousel    [Instagram Carousel] Meta API で Carousel 投稿（layer.png 必須）
  --twitter               Twitter (X) に投稿
  --instagram             Instagram Carousel（後方互換）
  --also-reel             Reel も投稿（--instagram と併用、後方互換）
```

### publish_tiktok_browser.py

```
python scripts/publish_tiktok_browser.py \
  --video PATH       動画ファイルパス（.mp4）
  --caption PATH     キャプションテキストファイルパス
  [--cookies PATH]   クッキー JSON パス（省略時: scripts/tiktok_cookies.json）
  [--auto]           投稿ボタンを自動クリック（確認なし）
```

### publish_instagram_reel.py

```
python scripts/publish_instagram_reel.py \
  --puzzle-id ID     パズル ID（例: 20260312_004）
  --dir PATH         素材ディレクトリ（caption 読み込みに使用）
  --base-url URL     GitHub Pages のベース URL
```

### publish_instagram_carousel.py

```
python scripts/publish_instagram_carousel.py \
  --dir PATH         素材ディレクトリ（layer.png 必須）
  --base-url URL     GitHub Pages のベース URL
```

---

## 付録：動画フォーマット仕様

| 項目 | 仕様 |
|------|------|
| 元動画 | `_full.mp4`（0-12s） |
| 0-2s | ピースが動く（フック） |
| 2-6s | 問題表示 |
| 6-9s | 考える時間 |
| 9-12s | 解答 |
| TikTok cut | 0-8s（解答なし） |
| Instagram cut | 0-12s（解答あり = full と同じ） |

> 動画は必ず動きから始めること（静止盤面スタート禁止）。
> TikTok アルゴリズムは冒頭 2-3 秒の動きで視聴継続率が決まるため。
