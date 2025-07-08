# コントリビューションガイド / Contributing Guide

> SoChi BLOCKS への貢献に興味を持っていただきありがとうございます！
> Thank you for contributing to **SoChi BLOCKS**.

---

## 📚 目次 / Table of Contents

1. [はじめに / Getting Started](#はじめに--getting-started)
2. [開発フロー / Development Workflow](#開発フロー--development-workflow)
3. [ブランチモデル / Branch Model](#ブランチモデル--branch-model)
4. [コミットメッセージ規約 / Commit Convention](#コミットメッセージ規約--commit-convention)
5. [Pull Request ガイド / Pull Request Guide](#pull-request-ガイド--pull-request-guide)
6. [Issue & Discussion](#issue--discussion)
7. [コードスタイル / Code Style](#コードスタイル--code-style)
8. [ライセンス / License](#ライセンス--license)

---

## はじめに / Getting Started

* **README の [Getting Started](README.md#getting-started) セクション** に従って開発環境をセットアップしてください。
* Python 3.11 + venv/pip、PostgreSQL 16、Node.js 18 が前提です。
* 不明点は GitHub Discussions で気軽に質問してください。

## 開発フロー / Development Workflow

```text
fork → clone → feat ブランチ作成 → 変更 → commit → push → Pull Request
```

1. `dev` ブランチを最新に rebase してから作業してください。
2. Draft PR で途中共有 OK。レビューコメントで議論を進めます。
3. CI が green になったら Maintainer がマージします。

## ブランチモデル / Branch Model

| ブランチ     | 用途                             |
| -------- | ------------------------------ |
| `main`   | 本番 (production) リリース用／タグ付与     |
| `dev`    | 統合 (integration) ブランチ／次期リリース準備 |
| `feat/*` | 機能開発／バグ修正用の短命ブランチ              |

## コミットメッセージ規約 / Commit Convention

Conventional Commits + **日本語サマリ OK**。

```
<type>(<scope>): <summary>

<body>  # 省略可
```

| type       | 用途     | 例                                   |
| ---------- | ------ | ----------------------------------- |
| `feat`     | 新機能    | `feat(ui): 3Dビュー回転を追加`              |
| `fix`      | バグ修正   | `fix(api): 500 エラーを解消`              |
| `docs`     | ドキュメント | `docs(readme): Getting Started を更新` |
| `refactor` | リファクタ  | `refactor(db): スキーマ整理`              |
| `chore`    | 依存更新など | `chore(deps): bump three.js`        |

## Pull Request ガイド / Pull Request Guide

* タイトルは `<type>: <要約>` 形式で簡潔に。
* PR テンプレのチェックリストを埋めてください。
* スクリーンショットや GIF があるとレビューしやすくなります。

## Issue & Discussion

* **不具合報告**: Issue へ。再現手順・期待結果・ログを添付してください。
* **質問・提案**: GitHub Discussions へ。Slack/Discord が立ち上がるまではここが最速窓口です。

## コードスタイル / Code Style

| 言語     | ツール           | コマンド                         |
| ------ | ------------- | ---------------------------- |
| Python | black + isort | `pre-commit run --all-files` |
| JS/TS  | prettier      | `npm run format`             |

> コミット前に `pre-commit install` を実行すると自動整形がかかります。

## ライセンス / License

* **ソースコード**: MIT License
* **教材・画像**: Creative Commons BY‑SA 4.0

> By submitting a contribution, you agree to license your work under these terms.
