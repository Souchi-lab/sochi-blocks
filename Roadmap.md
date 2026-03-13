---
title: "SoChi BLOCKS Roadmap"
version: "0.2.0"
owner: "SoChi-lab"
last_updated: "2026-03-08"
status: "active"
tags: [roadmap, timeline, governance]
---

# 🗺️ SoChi BLOCKS｜開発ロードマップ

> **目的**: Vision を現実に落とし込み、誰が・いつ・何を作るかを一元管理する。

---

## フェーズ一覧

| Phase                    | 期間 (目安)        | 主目的                                     | 状態             |
| ------------------------ | -------------- | --------------------------------------- | -------------- |
| **0. Project Init**      | 2025‑07        | CoC / Contrib / Governance / README     | ✅ Done         |
| **1. Core MVP**          | 2025‑08〜2026‑02 | DB / 3D Viewer / PDF / インタラクション        | ✅ Done         |
| **2. SNS & Automation**  | 2026‑02〜2026‑03 | SNS 自動投稿 / 動画生成 / パズル自動配信              | ✅ Done         |
| **3. Public Growth**     | 2026‑04〜       | UX 改善 / ユーザ獲得 / コミュニティ / i18n / 対戦機能  | 🔜 Next         |

---

## Phase 0 — Project Init (✅ 完了)

| ID    | Deliverable          | Status   | 備考                    |
| ----- | -------------------- | -------- | --------------------- |
| P0‑01 | `CODE_OF_CONDUCT.md` | ✅ Done   | PR merged             |
| P0‑02 | `CONTRIBUTING.md`    | ✅ Done   | PR merged             |
| P0‑03 | `GOVERNANCE.md`      | ✅ Done   | PR merged             |
| P0‑04 | `README.md`          | ✅ Done   | 初版完成・継続更新中            |

---

## Phase 1 — Core MVP (✅ 完了)

> 当初は 2025‑09 末目標だったが、機能範囲を大幅に拡張しながら 2026‑02 に完成。

| ID    | Deliverable                          | Status    | 備考                                             |
| ----- | ------------------------------------ | --------- | ------------------------------------------------ |
| P1‑01 | DB スキーマ（パズル定義・メタ情報）               | ✅ Done    | PostgreSQL + `db/migrations/`                    |
| P1‑02 | 3D Viewer MVP（Three.js + React + TS） | ✅ Done    | Vite ビルド、WebGL レンダリング                          |
| P1‑03 | PDF 自動生成 v1（教材テンプレ）                 | ✅ Done    | `backend/scripts/generate_puzzle_pdf.py`         |
| P1‑04 | インタラクティブ ピース配置                      | ✅ Done    | ドラッグ・クリック・キーボード操作 (WASD/QE/R/Enter) |
| P1‑05 | 3D 回転・配置コア                          | ✅ Done    | 24方向ユニーク回転、ゴーストプレビュー                          |
| P1‑06 | ゲーム UI/UX 改善                        | ✅ Done    | チュートリアル、勝利画面、ミス表示、答え表示、シェア画面              |
| P1‑07 | パズルコンテンツ整備                          | ✅ Done    | 70+ パズル JSON（`public/puzzles/`）                |

---

## Phase 2 — SNS & Automation (✅ 完了)

> 毎日の自動配信パイプラインが稼働中。

| ID    | Deliverable                          | Status    | 備考                                                    |
| ----- | ------------------------------------ | --------- | ------------------------------------------------------- |
| P2‑01 | SNS 動画自動生成                         | ✅ Done    | `backend/scripts/generate_puzzle_video.py` (Playwright) |
| P2‑02 | Instagram 画像自動生成                   | ✅ Done    | `scripts/generate_instagram_images.py`                  |
| P2‑03 | Twitter (X) 自動投稿                    | ✅ Done    | `scripts/publish_twitter.py`（リンク投稿 / Free Tier 対応）  |
| P2‑04 | Instagram 自動投稿                      | ✅ Done    | `scripts/publish_instagram.py`（Meta Graph API）         |
| P2‑05 | 一括自動配信スクリプト                        | ✅ Done    | `scripts/auto_publish.py`（難易度指定・日次スケジュール対応）       |
| P2‑06 | SNS カメラ軌道最適化（3D オービット）            | ✅ Done    | パズル中心固定の水平・垂直スムーズ軌道                               |

---

## Phase 3 — Public Growth (🔜 次フェーズ)

*Phase 2 完了を受けて、以下を優先度順に計画中。*

| ID    | Deliverable                     | Status    | 備考                                 |
| ----- | ------------------------------- | --------- | ------------------------------------ |
| P3‑01 | ランディングページ / 公式 Web サイト        | 📋 Todo   | SEO、パズル一覧、ソーシャルリンク               |
| P3‑02 | 認証・ユーザアカウント                    | 📋 Todo   | スコア保存、ランキング                         |
| P3‑03 | リアルタイム対戦                        | 📋 Todo   | WebSocket / Phase 2 後半              |
| P3‑04 | 教材投稿 UI（管理コンソール）               | 📋 Todo   | 外部クリエイターが問題を追加可能に                 |
| P3‑05 | i18n 多言語対応（EN / JA / ZH）       | 📋 Todo   |                                      |
| P3‑06 | Docker Compose 本番運用             | 📋 Todo   | `infra/docker/` 整備済み、Compose 化が残り  |
| P3‑07 | コミュニティ（Discord）                 | 📋 Todo   | ユーザ数 100 人達成後に開設予定                |

---

> **マイルストーン**: Phase 3 は SNS フォロワー・エンゲージメント成果を見ながら優先度を随時更新する。
