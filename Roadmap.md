---

title: "SoChi BLOCKS Roadmap"
version: "0.1.3"  # Phase 表復活 & Phase 1 主要タスク追加
owner: "SoChi‑lab"
last\_updated: "2025-07-08"
status: "draft"
tags: \[roadmap, timeline, governance]
--------------------------------------

# 🗺️ SoChi BLOCKS｜開発ロードマップ

> **目的**: Vision を現実に落とし込み、誰が・いつ・何を作るかを一元管理する。メタコメント (`<!-- deliverable:… task:… milestone:… status:… -->`) は GitHub Actions で JSON 化し、進捗レポート生成に利用。

---

## フェーズ一覧

| Phase                    | 期間 (目安)    | 主目的                                 | マイルストーン  | 状態             |
| ------------------------ | ---------- | ----------------------------------- | -------- | -------------- |
| **0. Project Init**      | 2025‑07    | CoC / Contrib / Governance / README | P0‑04 完了 | ✅ Done         |
| **1. Core Foundation**   | 2025‑08〜09 | DB 拡張 / 3D Viewer MVP / PDF v1      | P1‑05 完了 | 🚧 In Progress |
| **2. Advanced Features** | 2025‑10〜12 | リアルタイム対戦 / 教材投稿 UI / i18n           | P2‑06 完了 | ⏳ Planned      |
| **3. Public Release**    | 2026‑01    | β公開 & 初期ユーザテスト                      | P3‑02 完了 | ⏳ Planned      |

---

## Phase 0 — Project Init (✔︎ 完了)

| ID    | Deliverable          | Status        | 担当           | 備考                                                                                     |
| ----- | -------------------- | ------------- | ------------ | -------------------------------------------------------------------------------------- |
| P0‑01 | `CODE_OF_CONDUCT.md` | **Done**      | Project Lead | PR #1 merged <!-- deliverable:CoC task:P0-01 milestone:Phase0 status:done -->          |
| P0‑02 | `CONTRIBUTING.md`    | **Done**      | Maintainers  | PR #2 merged <!-- deliverable:Contributing task:P0-02 milestone:Phase0 status:done --> |
| P0‑03 | `GOVERNANCE.md`      | **Done**      | Project Lead | PR #3 merged <!-- deliverable:Governance task:P0-03 milestone:Phase0 status:done -->   |
| P0‑04 | Core `README.md`     | **In review** | Maintainers  | Draft in Canvas <!-- deliverable:Readme task:P0-04 milestone:Phase0 status:review -->  |

> **マイルストーン完了条件**: P0‑04 レビュー完了後、Phase 0 を Close。

---

## Phase 1 — Core Foundation (🚧 In Progress)

| ID    | Deliverable                 | Status   | 担当           | 備考                                                                    |
| ----- | --------------------------- | -------- | ------------ | --------------------------------------------------------------------- |
| P1‑01 | DB スキーマ拡張（パズル定義・メタ情報）       | **Todo** | Backend Dev  | <!-- deliverable:Schema task:P1-01 milestone:Phase1 status:todo -->   |
| P1‑02 | 3D Viewer MVP（回転・ズーム・ピース配置） | **Todo** | Frontend Dev | <!-- deliverable:3DViewer task:P1-02 milestone:Phase1 status:todo --> |
| P1‑03 | PDF 自動生成 v1（教材テンプレ）         | **Todo** | Backend Dev  | <!-- deliverable:PDFv1 task:P1-03 milestone:Phase1 status:todo -->    |
| P1‑04 | 教材管理 UI（CRUD）               | **Todo** | Full‑stack   | <!-- deliverable:AdminUI task:P1-04 milestone:Phase1 status:todo -->  |
| P1‑05 | 基本 API（認証 / コンテンツ取得）        | **Todo** | Backend Dev  | <!-- deliverable:API task:P1-05 milestone:Phase1 status:todo -->      |

> **想定マイルストーン**: 2025‑09 末までに P1‑05 まで完了。

---

## Phase 2 — Advanced Features (⏳ Planned)

*詳細タスクは Phase 1 完了時にブレイクダウン予定*

---

## Phase 3 — Public Release (⏳ Planned)

*詳細タスクは Phase 2 完了時にブレイクダウン予定*
