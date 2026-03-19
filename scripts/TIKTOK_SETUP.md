# TikTok 半自動投稿 セットアップガイド

SoChi BLOCKS の TikTok 投稿は **Playwright ブラウザ自動化** による半自動方式です。
「動画添付・キャプション入力・投稿ボタン有効化」まで自動化し、
最終的な **[Post] ボタンのクリックは手動** で行います。

---

## 前提

- Python 3.13+, Poetry 環境が動いていること
- Playwright はすでに `pyproject.toml` の依存に含まれています

---

## Step 1: Chromium をインストール

```bash
poetry run playwright install chromium
```

初回のみ必要です。Chromium バイナリが
`%USERPROFILE%\AppData\Local\ms-playwright\` にダウンロードされます。

---

## Step 2: TikTok にログインしてクッキーを保存

**2-1. Chrome で TikTok にログインする**

1. Google Chrome を開く
2. `https://www.tiktok.com` を開く
3. 投稿に使うアカウントでログインする

**2-2. クッキーをエクスポートする**

Chrome 拡張機能を使います（どちらでも可）：

- **EditThisCookie** — `https://www.editthiscookie.com/`
- **Cookie-Editor** — `https://cookie-editor.com/`

手順：
1. 拡張機能をインストールして `https://www.tiktok.com` を開く
2. 拡張機能のアイコンをクリック → **Export** → **JSON 形式**でコピー
3. 以下のパスに保存する：

```
scripts/tiktok_cookies.json
```

> このファイルは `.gitignore` に登録済みです。絶対にコミットしないでください。

**クッキーの有効期限**
TikTok のセッションは数週間〜数ヶ月持続します。
ログインが弾かれたら Step 2 を再実行してください。

---

## Step 3: 単体実行（1本投稿の準備）

```bash
# プロジェクトルートから実行
poetry run python scripts/publish_tiktok_browser.py \
  --video docs/sns_videos/20260312_007_full.mp4 \
  --caption docs/images/20260312/007/caption.txt
```

**実行すると：**

1. Chrome が自動で起動して TikTok アップロード画面が開きます
2. 動画が自動でアップロードされます
3. キャプションが自動で入力されます
4. `[Post]` ボタンが押せる状態になったら以下が表示されます：

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

5. ブラウザで `[Post]` をクリックして投稿します
6. ターミナルで Enter を押してブラウザを閉じます

---

## Step 4: auto_publish.py に統合して実行

```bash
# パズル生成 → Instagram → TikTok を一括実行
poetry run python scripts/auto_publish.py --all --instagram --tiktok

# TikTok だけ準備する（パズル生成なし・既存ディレクトリ指定）
poetry run python scripts/auto_publish.py \
  --dir docs/images/20260312/007 \
  --tiktok
```

`--tiktok` は `--instagram` とは完全に独立して動作します。
どちらか一方だけ指定することも可能です。

---

## 動画の優先順位

`auto_publish.py --tiktok` 実行時は以下の順で動画を探します：

1. `docs/sns_videos/{code}_full.mp4`   ← 推奨（full play）
2. `docs/sns_videos/{code}_teaser.mp4`
3. `docs/sns_videos/{code}.mp4`

---

## キャプションの優先順位

1. `docs/images/{date}/{seq}/caption_tiktok.txt`  ← TikTok 専用（将来用）
2. `docs/images/{date}/{seq}/caption.txt`         ← 既存の共通キャプション

TikTok 専用のキャプションが必要になったら `caption_tiktok.txt` を作成してください。

---

## CLI オプション一覧

| オプション | デフォルト | 説明 |
|-----------|-----------|------|
| `--video` | (必須) | 投稿する動画ファイルのパス |
| `--caption` | (必須) | キャプションファイルのパス |
| `--cookies` | `scripts/tiktok_cookies.json` | クッキーファイルのパス |
| `--auto` | 無効 | 投稿ボタンを自動クリック（注意：即時公開） |

---

## セレクタが壊れた場合

TikTok の UI 更新でセレクタが変わった場合：

```bash
# TikTok のアップロード画面でセレクタを再取得する
poetry run playwright codegen https://www.tiktok.com/upload
```

2つのウィンドウが開き、操作に対応するコードがリアルタイム生成されます。
生成されたセレクタを `publish_tiktok_browser.py` の以下の変数に反映してください：

```python
_FILE_INPUT_SELECTORS = [...]
_CAPTION_SELECTORS = [...]
_POST_BUTTON_SELECTORS = [...]
```

---

## 想定されるエラーと対処

| エラーメッセージ | 原因 | 対処 |
|----------------|------|------|
| `Cookie file not found` | クッキーファイルが未作成 | Step 2 を実施 |
| `TikTok session is invalid` | セッション期限切れ | Step 2 を再実施 |
| `Could not find file upload input` | TikTok UI 変更 | `playwright codegen` でセレクタ更新 |
| `Timed out waiting for video encoding` | 動画が大きい / 回線が遅い | タイムアウト値を `ENCODING_TIMEOUT_S` で調整 |
| `Post button did not become enabled` | 設定が未完了の可能性 | ブラウザでプライバシー設定を確認 |

---

## 完全自動化に向けたロードマップ

```
Phase 1（現在）: 半自動投稿
  - 動画アップロード・キャプション入力まで自動
  - [Post] ボタンは手動クリック

Phase 2（将来）: --auto で完全自動
  - publish_tiktok_browser.py --auto を使う
  - クッキーの自動更新スクリプトを整備

Phase 3（将来）: TikTok 公式 API に移行
  - API 審査が通過した段階で Playwright を廃止
  - publish_tiktok_api.py として別スクリプトに切り替え
  - auto_publish.py の --tiktok オプションはそのまま維持
```
