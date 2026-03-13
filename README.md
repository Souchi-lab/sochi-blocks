# SoChi BLOCKS

> **昔ムズかったパズル、いまなら親子で解ける！！**  
> *SoChi BLOCKS* は、**実物ピース × 3D インタラクティブゲーム × PDF 教材 × SNS 自動配信** を組み合わせて、子どもの "立体脳" とワクワクを同時に育てる STEM ブロック教材です。

![SoChi BLOCKS Logo](docs/images/logo_placeholder.png)

---

## 📸 Screenshots

| 3D Viewer (インタラクティブ)                        | PDF 教材サンプル                          | 実物ブロック写真                              |
| -------------------------------------------- | ------------------------------------ | --------------------------------------- |
| ![3D View](docs/images/webviewer_sample.gif) | ![PDF1](docs/images/cube_sample_1.jpg) | ![Photo](docs/images/cube_sample_2.jpg) |
|                                              | ![PDF2](docs/images/cube_sample_3.jpg) |                                         |

---

## ✨ 主な機能

| 機能 | 詳細 |
|------|------|
| 🎮 **インタラクティブ 3D パズル** | Three.js + React。ピースをクリック・WASD キー操作で配置。ゴーストプレビュー・ミスカウント・クリアタイム計測付き |
| 🔄 **24 方向ユニーク回転** | 全方向の回転候補をサムネイル表示。配置可能な向きだけハイライト |
| 📄 **PDF 教材自動生成** | パズル問題・解答・3D 図解を PDF に自動出力 |
| 🎬 **SNS 動画自動生成** | Playwright でブラウザ操作を自動録画。カメラがパズルを中心にオービット |
| 📱 **SNS 自動投稿** | Twitter (X) & Instagram に毎日パズルを自動配信 |
| 📦 **70+ パズルコンテンツ** | JSON ベースのパズル定義。難易度 3 段階 (easy / medium / hard) |
| 📖 **チュートリアル** | 初回起動時に操作方法をガイド表示（localStorage で管理） |
| 🏆 **勝利・シェア画面** | クリア後にタイム・ミス数を表示、SNS シェアリンク生成 |

---

## 📱 SNS 配信戦略

SoChi BLOCKS のコンテンツ戦略は **「発見 → カタログ → 体験」** の三層構造。

| SNS | 役割 | 動画 | キャプション |
|-----|------|------|------------|
| **TikTok** | 🔍 発見 — 新規ユーザー獲得 | `_tiktok.mp4`（0-8s、解答なし） | 短文・フック重視 |
| **Instagram Reel** | 🎨 ブランド — フォロワー継続配信 | `_instagram.mp4`（0-12s、解答あり） | 説明型・保存促進 |
| **Instagram Carousel** | 📚 カタログ — パズル図鑑化 | 動画 + 画像 | 説明型 |

### Instagram Carousel のカバー画像について

Instagram プロフィールを **パズル図鑑** のように見せるため、
Carousel の先頭画像は必ず `layer.png`（パズルレイヤー図）を使用します。

```
layer.png = カタログ表紙（必須）
```

`layer.png` が存在しない場合、`publish_instagram_carousel.py` はエラーを出力して停止します。

### 投稿コマンド

```bash
# TikTok（発見）
python scripts/auto_publish.py --difficulty hard --tiktok

# Instagram Reel（ブランド）
python scripts/auto_publish.py --difficulty hard --instagram-reel

# Instagram Carousel（カタログ）
python scripts/auto_publish.py --difficulty hard --instagram-carousel

# 全 SNS 一括
python scripts/auto_publish.py --all --tiktok --instagram-reel --instagram-carousel
```

### ディレクトリ構造（SNS 素材）

```
docs/
 ├ images/
 │   └ YYYYMMDD/
 │        └ PUZZLE_ID/
 │            layer.png              ← Carousel カバー（必須）
 │            caption_tiktok.txt     ← TikTok 用キャプション
 │            caption_instagram.txt  ← Instagram 用キャプション
 │            caption_twitter.txt    ← Twitter 用キャプション
 │            puzzle.json
 │
 └ sns_videos/
        YYYYMMDD_XXX_full.mp4        ← 元動画（0-12s）
        YYYYMMDD_XXX_tiktok.mp4      ← TikTok 用（0-8s trim）
        YYYYMMDD_XXX_instagram.mp4   ← Instagram 用（full コピー）
```

---

## 🚀 Getting Started

最小構成でサクッと動かすための手順です。依存は **Python 3.11**, **Node.js 18 LTS** のみ！

```bash
# 1. Clone
git clone https://github.com/sochi-lab/sochi-blocks.git
cd sochi-blocks

# 2. Python 仮想環境 & 依存
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# 3. フロントエンド依存 & 開発サーバ (Vite)
npm install --prefix frontend
npm run dev --prefix frontend    # → http://localhost:5173/

# 4. パズルを開く (例)
# http://localhost:5173/?puzzle_id=20260308_001
# 難易度付き問題: ?puzzle_id=20260308_001&removed_pieces=A,B
```

### SNS 自動配信を動かす

```bash
# .env に API キーを設定してから:
python scripts/auto_publish.py --difficulty easy
```

---

## 🛠️ Tech Stack

| Layer | 技術 |
|-------|------|
| **Frontend** | React 18 + TypeScript + Vite, Three.js (WebGL 3D) |
| **Puzzle Logic** | 自前の 3D 回転計算エンジン (utils/rotations.ts) |
| **PDF 生成** | Python + reportlab / fpdf2 |
| **動画生成** | Playwright (ブラウザ自動操作 → MP4) |
| **SNS 投稿** | Twitter API v2, Meta Graph API (Instagram) |
| **DB** | PostgreSQL 16 (マイグレーション: `db/migrations/`) |
| **インフラ** | Docker (`infra/docker/`) |

---

## 🛠️ Branch Model

| Branch   | 用途                        |
| -------- | ------------------------- |
| `main`   | Production / Release タグ専用 |
| `dev`    | Integration (次リリース候補)     |
| `feat/*` | 機能開発用短命ブランチ               |

### Conventional Commits (日本語サマリ OK)

```text
feat(ui): 3Dビューワを追加
fix(api): スコア計算バグを修正
```

PR テンプレは `.github/pull_request_template.md` を参照してください。

---

## 🤝 Community

| 窓口                 | URL                                                                                                            | 用途             |
| ------------------ | -------------------------------------------------------------------------------------------------------------- | -------------- |
| GitHub Issues      | [issues](https://github.com/sochi-lab/sochi-blocks/issues)                                                     | バグ報告・機能要望      |
| GitHub Discussions | [discussions](https://github.com/sochi-lab/sochi-blocks/discussions)                                           | Q&A・雑談・提案     |
| Discord (予定)       | フォロワー 100 人達成後に開設予定                                                                                           | リアルタイム雑談・ハンズオン |

---

## 📜 License

- **Source code**: MIT License – see [`LICENSE`](./LICENSE)
- **Educational content & images**:  
  Creative Commons Attribution-ShareAlike 4.0 International  
  (CC BY-SA 4.0) – see <https://creativecommons.org/licenses/by-sa/4.0/>

---

## ✨ Credits & Thanks

* **[Three.js](https://threejs.org/)** — WebGL 3D rendering
* **[Vite](https://vitejs.dev/)** — Frontend build tool
* **[Playwright](https://playwright.dev/)** — Browser automation for video generation
* **[Flask](https://flask.palletsprojects.com/)** — Python API micro‑framework
* **[fpdf2](https://pyfpdf.github.io/fpdf2/)** — PDF 自動生成
* Special thanks: @内藤亨介, SoChi 家のみなさん ほか

---

### 📮 Contact / お問い合わせ

* 提案・不具合報告は GitHub Issues へどうぞ！
* 行動規範違反の報告は `enuyama5287@gmail.com` までメールしてください。

<div align="center">
  Made with ❤️ & 🧩 in Japan
</div>
