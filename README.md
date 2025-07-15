# SoChi BLOCKS

> **昔ムズかったパズル、いまなら親子で解ける！！**
> *SoChi BLOCKS* は、**実物ピース × 3D ビュー × PDF 教材** を組み合わせて、子どもの “立体脳” とワクワクを同時に育てる STEM ブロック教材です。

![SoChi BLOCKS Logo](docs/images/logo_placeholder.png)

---

## 📸 Screenshots / Demo Gallery

|                3D Viewer (WIP)               |                PDF Sample               |               Physical Blocks              |
| :------------------------------------------: | :-------------------------------------: | :----------------------------------------: |
| ![3D View](docs/images/webviewer_sample.gif) | ![PDF 1](docs/images/cube_sample_1.jpg) | ![Blocks 1](docs/images/cube_sample_2.jpg) |
|                       —                      | ![PDF 2](docs/images/cube_sample_3.jpg) |                      —                     |

> **Note**: スクリーンショット・GIF は開発中のものです。最新 UI は `docs/images/` 内で随時更新します。

---

## 🚀 Getting Started

**`.env` ファイルの準備:**
プロジェクトルートに `.env` ファイルを作成し、以下の内容を記述してください。

```
# .env
DATABASE_URL=postgresql://postgres:example@localhost:5432/sochi_blocks
```

最小構成でサクッと動かすための手順です。依存は **Python 3.11**, **Node.js 18 LTS**, **PostgreSQL 16** のみ！

```bash
# 1. Clone
$ git clone https://github.com/sochi-lab/sochi-blocks.git
$ cd sochi-blocks

# 2. Python 仮想環境 & 依存
$ python -m venv .venv
$ source .venv/bin/activate               # Windows: .venv\Scripts\activate
$ pip install -r requirements.txt         # Flask, psycopg2, etc.

# 3. DB セットアップ (ローカル PostgreSQL)
$ createdb sochi_blocks_dev
$ psql sochi_blocks_dev -f backend/schema.sql

# 4. バックエンド起動 (Flask API)
$ set FLASK_APP=backend/app.py            # mac/Linux: export FLASK_APP=backend/app.py
$ set DATABASE_URL=postgresql://localhost/sochi_blocks_dev
$ flask run -h 0.0.0.0 -p 5000

# 5. フロントエンド依存 & 開発サーバ (Vite)
$ npm install --prefix frontend
$ npm run dev  --prefix frontend           # → http://localhost:5173/
```

> 🐳 **Docker 派のあなたへ** — 本番環境用に `docker-compose.yml` を用意予定。Issue #12 で議論中です。

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

| 窓口                                                                          | 用途             |
| --------------------------------------------------------------------------- | -------------- |
| [GitHub Issues](https://github.com/sochi-lab/sochi-blocks/issues)           | バグ報告・機能要望      |
| [GitHub Discussions](https://github.com/sochi-lab/sochi-blocks/discussions) | Q\&A・提案        |
| Discord (予定)                                                                | リアルタイム雑談・ハンズオン |

> Slack Workspace / Slack Connect は Phase 6 **Community Growth** 以降で検討。

---

## 📇 License

* **Source code**: MIT License – see [`LICENSE`](./LICENSE)
* **Educational content & images**: Creative Commons Attribution‑ShareAlike 4.0 International (CC BY‑SA 4.0) – see [https://creativecommons.org/licenses/by-sa/4.0/](https://creativecommons.org/licenses/by-sa/4.0/)

---

## ✨ Credits & Thanks

* **[Three.js](https://threejs.org/)** — WebGL 3D rendering
* **[Flask](https://flask.palletsprojects.com/)** — Python API micro‑framework
* **[PyFPDF](https://pyfpdf.github.io/)** — PDF 自動生成
* Special thanks: @内藤亨介, SoChi 家のみなさん ほか

---

### 📮 Contact / お問い合わせ

* 提案・不具告報は GitHub Issues へどう！
* 行動規範違反の報告は `enuyama5287@gmail.com` までメールしてください。

<div align="center">
  Made with ❤️ & 🧩 in Japan
</div>